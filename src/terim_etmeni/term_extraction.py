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
document. Exclude document-specific participants, actions, events, states, or
descriptions (for example: attacker nodes, honest chain, best effort basis,
block broadcasts, chronological order). When unsure, return fewer terms.

QUALIFYING EXAMPLES (return these kinds of terms):
context window, packet switching, access control, distributed computing,
fault tolerance, retrieval-augmented generation, distributed transactions.

NON-QUALIFYING EXAMPLES (never return these):
recent study, significant result, proposed approach, large number,
experimental result.

You must NOT extract ordinary English words, generic academic phrases, person
names, institution or company names, product names (unless used as a genuine
technical concept), code or variables, hyperparameters, pseudo-code, dataset or
model names, benchmark labels, figure/table/equation labels, complete sentences,
section headings, references, or citations. If the text contains no eligible
technical concept, return an empty list. Do not translate, infer, or normalize
terms; preserve the spelling as found in the text.
Return only one complete JSON object matching the schema."""


USER_TASK = """TASK
Extract the technical terms from the text between TEXT START and TEXT END that are
worth adding to an English computing dictionary. Return only terms that occur
verbatim in the text. A short accurate list is better than an exhaustive one.
Return no more than 8 terms. Do not turn ordinary phrases about this document's
actors, events, or conditions into dictionary entries.

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
