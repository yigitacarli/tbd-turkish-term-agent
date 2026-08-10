"""Model adaylarını birleştirme ve kaynak metinle doğrulama."""
from __future__ import annotations

import re
import unicodedata
from collections import OrderedDict
from typing import Protocol

from .dictionary import normalized_key
from .models import ExtractedTerm, PageText, TermEvidence, TextChunk


class TermProvider(Protocol):
    def extract(self, text: str) -> list[ExtractedTerm]:
        ...


def _plausible_term(term: str) -> bool:
    words = term.split()
    if len(term) > 100 or len(words) > 8:
        return False
    if "\n" in term or ":" in term:
        return False
    if re.search(r"[?!]", term) or len(re.findall(r"\.(?:\s|$)", term)):
        return False
    if re.search(r"\b(?:AI|artificial intelligence)\s+in\s+", term, re.IGNORECASE):
        return False
    if re.search(
        r"\b(?:acts?|applies?|combines?|directs?|links?|orders?|performs?|"
        r"produced|receives?|removes?|retains?|selects?|updates?|uses?|used|"
        r"validates?|works?)\b",
        term,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"\b(?:abstract|conclusion|discussion|introduction|methodology|overview|"
        r"references|research note|results|sequence)\b$",
        term,
        re.IGNORECASE,
    ):
        return False
    if term.casefold() in {"experimental components"}:
        return False
    return True


def _search_pattern(term: str) -> re.Pattern[str]:
    normalized = unicodedata.normalize("NFKC", term).strip()
    parts = [re.escape(part) for part in re.split(r"[\s\-‐‑‒–—−]+", normalized) if part]
    body = r"[\s\-‐‑‒–—−]+".join(parts)
    if normalized and normalized[0].isalnum():
        body = r"(?<!\w)" + body
    if normalized and normalized[-1].isalnum():
        body += r"(?!\w)"
    return re.compile(body, flags=re.IGNORECASE | re.UNICODE)


def evidence_for(term: str, pages: list[PageText]) -> TermEvidence:
    pattern = _search_pattern(term)
    evidence = TermEvidence(term=term)
    for page in pages:
        count = len(pattern.findall(unicodedata.normalize("NFKC", page.text)))
        if count:
            evidence.pages.add(page.page)
            evidence.occurrence_count += count
    return evidence


def extract_verified_terms(
    chunks: list[TextChunk], pages: list[PageText], provider: TermProvider
) -> list[TermEvidence]:
    candidates: "OrderedDict[str, str]" = OrderedDict()
    for page in pages:
        for match in re.finditer(r'["“]([^"”]{2,100})["”]', page.text):
            term = " ".join(match.group(1).split()).strip(" \t\r\n,;:")
            if 2 <= len(term.split()) <= 8 and _plausible_term(term):
                candidates.setdefault(normalized_key(term), term)
    for chunk in chunks:
        prompt = "PAGE {}\n\n{}".format(chunk.page, chunk.text)
        for extracted in provider.extract(prompt):
            term = " ".join(extracted.term.split()).strip(" \t\r\n,;:")
            if (
                len(term) < 2
                or not any(character.isalpha() for character in term)
                or term.startswith(("http://", "https://"))
                or not _plausible_term(term)
            ):
                continue
            candidates.setdefault(normalized_key(term), term)

    verified = []
    for term in candidates.values():
        evidence = evidence_for(term, pages)
        if evidence.occurrence_count:
            verified.append(evidence)
    return verified
