"""PDF → terim adayları → sözlük karşılaştırması işlem hattı."""
from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from .chunker import chunk_pages
from .dictionary import DictionaryIndex, normalized_key, relaxed_key
from .models import TermEvidence
from .pdf_reader import read_pdf
from .term_extractor import TermProvider, evidence_for, extract_verified_terms


_GENERIC_SINGLE_WORDS = {
    "agriculture",
    "education",
    "entertainment",
    "dependencies",
    "music",
    "task",
    "worker",
}

_BRAND_PREFIXES = {
    "adobe",
    "amazon",
    "apple",
    "facebook",
    "google",
    "ibm",
    "meta",
    "microsoft",
    "netapp",
    "oracle",
}


def _low_confidence_missing(term: str) -> bool:
    words = term.split()
    if len(words) == 1:
        if term.isupper() and 2 <= len(term) <= 10:
            return False
        return True
    lowered = term.casefold()
    first_word = re.split(r"\s+", lowered, maxsplit=1)[0]
    if first_word in _BRAND_PREFIXES:
        return True
    if lowered in _GENERIC_SINGLE_WORDS:
        return True
    if re.match(r"^(?:application|applications) of\b", lowered):
        return True
    if re.search(r"\b(?:industry|industries)$", lowered):
        return True
    if lowered in {"travel & transport", "travel and transport"}:
        return True
    return False


def _canonical_candidate(term: str) -> str:
    return re.sub(
        r"^(?:different|multiple|several|various)\s+",
        "",
        term,
        flags=re.IGNORECASE,
    ).strip()


def _expand_model_evidence(
    evidence: list[TermEvidence], pages, dictionary: DictionaryIndex
) -> list[TermEvidence]:
    """Birleşmiş adayları ayırır ve gereksiz niceleyicileri kaldırır."""
    expanded: list[TermEvidence] = []
    for item in evidence:
        candidate = _canonical_candidate(item.term)
        status, _ = dictionary.lookup(candidate)
        parts = re.split(r"\s+and\s+", candidate, maxsplit=1, flags=re.IGNORECASE)
        if status == "missing" and len(parts) == 2:
            left, right = (part.strip(" ,;:") for part in parts)
            if 2 <= len(left.split()) <= 6 and 2 <= len(right.split()) <= 6:
                split_evidence = [evidence_for(left, pages), evidence_for(right, pages)]
                if all(value.occurrence_count for value in split_evidence):
                    expanded.extend(split_evidence)
                    continue
        if candidate != item.term:
            item = evidence_for(candidate, pages)
        if item.occurrence_count:
            expanded.append(item)
    return expanded


def _merge_dictionary_evidence(
    evidence: list[TermEvidence], pages, dictionary: DictionaryIndex
) -> list[TermEvidence]:
    """Model sonuçlarına PDF'de doğrudan bulunan sözlük terimlerini ekler."""
    merged: "OrderedDict[str, TermEvidence]" = OrderedDict(
        (normalized_key(item.term), item) for item in evidence
    )
    existing_relaxed = {relaxed_key(item.term) for item in evidence}
    for page in pages:
        for term, count in dictionary.find_phrases(page.text):
            key = normalized_key(term)
            if key in merged or relaxed_key(term) in existing_relaxed:
                continue
            item = TermEvidence(term=term)
            item.pages.add(page.page)
            item.occurrence_count = count
            merged[key] = item
            existing_relaxed.add(relaxed_key(term))
    # Aynı sözlük terimi başka sayfalarda da geçiyorsa kanıtını tamamla.
    for key, item in list(merged.items()):
        status, _ = dictionary.lookup(item.term)
        if status == "exact":
            verified = evidence_for(item.term, pages)
            if verified.occurrence_count:
                merged[key] = verified
            else:
                del merged[key]
    return list(merged.values())


def _translations(entries: list[dict[str, object]]) -> list[str]:
    return list(
        dict.fromkeys(
            entry["tr"]
            for entry in entries
            if isinstance(entry.get("tr"), str)
        )
    )


def analyze_pdf(
    pdf_path: Path,
    dictionary: DictionaryIndex,
    provider: TermProvider,
    model_name: str,
    chunk_size: int = 3_000,
    chunk_overlap: int = 200,
) -> dict[str, object]:
    pages = read_pdf(pdf_path)
    chunks = chunk_pages(pages, size=chunk_size, overlap=chunk_overlap)
    model_evidence = extract_verified_terms(chunks, pages, provider)
    evidence = _expand_model_evidence(model_evidence, pages, dictionary)
    evidence = _merge_dictionary_evidence(evidence, pages, dictionary)

    found: list[dict[str, object]] = []
    possible: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    for item in evidence:
        status, entries = dictionary.lookup(item.term)
        base = item.as_dict()
        if status == "exact":
            base["translations"] = _translations(entries)
            found.append(base)
        elif status == "possible":
            base["possible_dictionary_terms"] = [
                {"en": entry["en"], "tr": entry["tr"]}
                for entry in entries
                if isinstance(entry.get("en"), str)
                and isinstance(entry.get("tr"), str)
            ]
            possible.append(base)
        else:
            if _low_confidence_missing(item.term):
                base["reason"] = "low_confidence_single_word"
                rejected.append(base)
            else:
                missing.append(base)

    found.sort(key=lambda item: str(item["term"]).casefold())
    possible.sort(key=lambda item: str(item["term"]).casefold())
    missing.sort(key=lambda item: str(item["term"]).casefold())
    rejected.sort(key=lambda item: str(item["term"]).casefold())
    version = dictionary.metadata.get("version")
    return {
        "document": Path(pdf_path).name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "dictionary_version": version,
        "page_count": len(pages),
        "verified_candidate_count": len(evidence),
        "counts": {
            "dictionary_matches": len(found),
            "possible_matches": len(possible),
            "missing_terms": len(missing),
            "rejected_candidates": len(rejected),
        },
        "dictionary_matches": found,
        "possible_matches": possible,
        "missing_terms": missing,
        "rejected_candidates": rejected,
    }
