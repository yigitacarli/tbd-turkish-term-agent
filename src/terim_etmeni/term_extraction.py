"""LLM tabanlı teknik terim çıkarımı ve muhafazakâr normalizasyon.

Bu modül sade işlem hattının ilk adımıdır: LLM yalnızca teknik terim adayı
üretir, sözlük üyeliği kararını vermez (ADR-002). Sözlük karşılaştırması
:mod:`terim_etmeni.pipeline` içindeki deterministik katmanda yapılır.

Burada LLM'e sözlük verilmez ve "bu terim sözlükte var mı?" diye sorulmaz.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Protocol

from terim_etmeni.models import ExtractedTerm, PageText, TextChunk

# Kısa çizgi ve çeşitli Unicode tireler; canonical normalizasyonda boşluğa çevrilir.
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212-"


SYSTEM_PROMPT = """You are a precise English technical-terminology extractor for academic PDFs.
Your ONLY task is to read the supplied text and return the technical concepts from
computing, software, AI, data, networking, security, or digital systems that would
be worth adding to an English computing terminology dictionary.

Return ONLY terms that occur verbatim in the text. Prefer precise multi-word
phrases; include a single technical word or an established abbreviation only when
omitting it would lose a distinct concept. Do not repeat the same term.

Return at most 8 terms from one text chunk. Select only stable technical concepts
that could be an independent computing-dictionary headword outside this specific
document. When unsure, return fewer terms.

QUALIFYING EXAMPLES (return these kinds of terms):
- Cryptographic & Security primitives: cryptographic proof, proof-of-work, digital signature, public-key cryptography, hash function, Merkle tree, nonce, zero-knowledge proof.
- Distributed Systems & Networking: peer-to-peer network, consensus mechanism, fault tolerance, packet switching, distributed timestamp server, state machine replication, consistent hashing, vector clock, simplified payment verification.
- Computing & AI: context window, retrieval-augmented generation, attention mechanism, gradient descent, convolutional layer, distributed transactions.

NON-QUALIFYING EXAMPLES (never return these):
- Hypothetical scenario participants, roles, or actors specific to a thought experiment, game-theoretic model, or protocol analysis (e.g., honest nodes, attacker chain, honest blocks, attacker node, honest chain, malicious peer, victim, challenger, parallel chain).
- Ordinary single English words or general non-computing concepts from economics, management, or everyday speech (e.g., incentive, acting, dependencies, causality, tools, evidence, seeds, mint, candidate, worker, cost, rules). A single English word must NEVER be extracted unless it is an established computer-science specific primitive (such as: mutex, semaphore, nonce, socket, hypervisor, deadlock).
- Narrative descriptions, explanatory clauses, or ad-hoc definition phrases (e.g., chain of digital signatures, public history of transactions, block broadcasts, client originated requests, verifiability of generated text). Extract only the standardized technical term itself (e.g., digital signature, transaction), not the surrounding explanatory phrase.
- Section titles, paragraph headings, or table labels (e.g., 1. Introduction, 6. Incentive, 8. Calculations).
- Experimental metrics, percentages, percentiles, or benchmarks (e.g., 99.9th percentile, 3-way classification, BLEU score, F1 score).
- Code variable names, function identifiers, or camelCase symbols (e.g., candidateId, AppendEntries, prevLogIndex, matchIndex).
- Generic academic phrases (e.g., recent study, proposed approach, experimental results).
- Generic numbers, dimensions, hyperparameters, or mathematical notations (e.g., d_model, learning rate, 512-dimensional).

You must NOT extract ordinary English words, generic academic phrases, person
names, institution or company names, product names (unless used as a genuine
technical concept), code or variables, hyperparameters, pseudo-code, dataset or
model names, benchmark labels, figure/table/equation labels, complete sentences,
section headings, references, or citations. If the text contains no eligible
technical concept, return an empty list: {"terms": []}. Do not translate, infer,
or normalize terms; preserve the spelling as found in the text.
Return only one complete JSON object matching the schema."""


USER_TASK = """TASK
Extract the technical terms from the text between TEXT START and TEXT END that are
worth adding to an English computing dictionary. Return only terms that occur
verbatim in the text. A short accurate list is better than an exhaustive one.
Return no more than 8 terms.

STRICT EXCLUSIONS (never return these):
- Hypothetical scenario actors / participant roles (e.g., honest nodes, attacker chain, honest blocks, attacker node).
- Ordinary single English words (e.g., incentive, acting, dependencies, causality, tools, seeds).
- Narrative explanatory phrases or definition clauses (e.g., chain of digital signatures, public history of transactions, block broadcasts).
- Benchmark statistics, code identifiers, section titles, or math notations.

If there are no qualifying technical terms in the text, return an empty list: {{"terms": []}}.

TEXT START
{text}
TEXT END"""


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "terms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["term"],
            },
        }
    },
    "required": ["terms"],
}


class TermExtractor(Protocol):
    """LLM sağlayıcısının yalnızca terim üreten arayüzü."""

    def extract_terms(self, text: str) -> list[ExtractedTerm]:
        ...


def normalize_term(value: str) -> str:
    """Hem sözlük anahtarlarına hem adaylara uygulanan muhafazakâr normalizasyon.

    - Unicode NFKC normalizasyonu
    - küçük harfe çevirme
    - tire/boşluk varyasyonlarını tek boşluğa indirgeme
    - baş/bitiş noktalamasını temizleme
    - yinelenen boşlukları daraltma

    Farklı teknik kavramları birleştirmez: ``large language model`` ile
    ``language model`` aynı anahtar üretmez.
    """
    value = unicodedata.normalize("NFKC", value)
    value = value.casefold()
    value = re.sub("[{}]".format(_DASHES), " ", value)
    value = value.strip()
    value = re.sub(r"^[\W_]+|[\W_]+$", "", value)
    return " ".join(value.split())


def _search_pattern(term: str) -> re.Pattern[str]:
    normalized = unicodedata.normalize("NFKC", term).strip()
    parts = [re.escape(part) for part in re.split("[{}]".format(_DASHES), normalized) if part]
    body = r"[\s{0}]+".format(_DASHES).join(parts)
    if normalized and normalized[0].isalnum():
        body = r"(?<!\w)" + body
    if normalized and normalized[-1].isalnum():
        body += r"(?!\w)"
    return re.compile(body, flags=re.IGNORECASE | re.UNICODE)


def term_occurrences(term: str, pages: list[PageText]) -> tuple[int, set[int]]:
    """Terimin belgede kaç kez ve hangi sayfalarda geçtiğini bulur."""
    pattern = _search_pattern(term)
    total = 0
    page_set: set[int] = set()
    for page in pages:
        count = len(pattern.findall(unicodedata.normalize("NFKC", page.text)))
        if count:
            total += count
            page_set.add(page.page)
    return total, page_set


def find_context(term: str, pages: list[PageText], limit: int = 240) -> str:
    """Terimin geçtiği ilk satırı bağlam olarak döndürür."""
    pattern = _search_pattern(term)
    for page in pages:
        for line in page.text.splitlines():
            line = " ".join(line.split())
            if pattern.search(unicodedata.normalize("NFKC", line)):
                if len(line) <= limit:
                    return line
                return line[:limit].rsplit(" ", 1)[0] + " …"
    return ""


def extract_terms_from_chunks(
    chunks: list[TextChunk],
    extractor: TermExtractor,
    extraction_warnings: list[str] | None = None,
) -> list[ExtractedTerm]:
    """Her parçadan terim çıkarır, normalize edilmiş anahtarla tekilleştirir."""
    results: list[ExtractedTerm] = []
    seen: set[str] = set()
    for chunk in chunks:
        try:
            extracted_terms = extractor.extract_terms(chunk.text)
        except RuntimeError as error:
            if extraction_warnings is None:
                raise
            extraction_warnings.append(
                "Sayfa {} (parça {}): {}".format(chunk.page, chunk.index + 1, error)
            )
            continue
        for extracted in extracted_terms:
            term = " ".join(str(extracted.term).split()).strip(" \t\r\n,;:")
            if (
                len(term) < 2
                or not any(character.isalpha() for character in term)
                or term.startswith(("http://", "https://"))
            ):
                continue
            key = normalize_term(term)
            if key and key not in seen:
                seen.add(key)
                results.append(ExtractedTerm(term=term))
    return results
