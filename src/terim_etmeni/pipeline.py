"""PDF → LLM terim çıkarımı → normalizasyon → sözlük arama → eksik terimler.

Sözlük üyeliği burada, normalize edilmiş İngilizce terimler üzerinden yalnızca
Python ``dict`` aramasıyla ve kesin eşleşmeyle karar verir (ADR-002). Model bu
karara katılmaz.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from terim_etmeni.chunker import chunk_pages
from terim_etmeni.pdf_reader import read_pdf

from .term_extraction import (
    TermExtractor,
    extract_terms_from_chunks,
    find_context,
    normalize_term,
    term_occurrences,
)


from terim_etmeni.dictionary import normalized_key, relaxed_key, singular_key


class TermDictionary:
    """Normalize edilmiş İngilizce terimler üzerinden deterministik sözlük."""

    def __init__(self, terms: list[dict[str, object]], metadata: dict | None = None) -> None:
        self.metadata = metadata or {}
        self._exact: dict[str, list[dict[str, object]]] = {}
        self._relaxed: dict[str, list[dict[str, object]]] = {}
        self._singular: dict[str, list[dict[str, object]]] = {}
        for entry in terms:
            if not isinstance(entry, dict):
                continue
            english = entry.get("en")
            if isinstance(english, str) and english.strip():
                item = dict(entry)
                norm = normalized_key(english)
                rel = relaxed_key(english)
                sing = singular_key(english)
                self._exact.setdefault(norm, []).append(item)
                self._relaxed.setdefault(rel, []).append(item)
                if sing:
                    self._singular.setdefault(sing, []).append(item)

    def lookup(self, term: str) -> tuple[bool, list[dict[str, object]], str]:
        """Sözlükte tam, gevşek ve tekil/çoğul normalizasyonuyla arama yapar.

        Returns:
            (bulundu_mu, eşleşen_girdiler, eşleşme_türü: 'exact' | 'singular_variant' | 'missing')
        """
        norm = normalized_key(term)
        exact = self._exact.get(norm)
        if exact:
            return True, exact, "exact"

        rel = relaxed_key(term)
        relaxed = self._relaxed.get(rel)
        if relaxed:
            return True, relaxed, "exact"

        sing = singular_key(term)
        if sing and sing != norm and sing != rel:
            sing_matches = self._relaxed.get(sing) or self._singular.get(sing) or self._exact.get(sing)
            if sing_matches:
                return True, sing_matches, "singular_variant"

        return False, [], "missing"

    def __len__(self) -> int:
        return len(self._exact)



def analyze_pdf(
    pdf_path: Path,
    dictionary: TermDictionary,
    extractor: TermExtractor,
    model_name: str,
    chunk_size: int = 6_000,
    chunk_overlap: int = 100,
    abbreviations=None,
) -> dict[str, object]:
    pages = read_pdf(pdf_path)
    chunks = chunk_pages(pages, size=chunk_size, overlap=chunk_overlap)
    extraction_warnings: list[str] = []
    candidates = extract_terms_from_chunks(chunks, extractor, extraction_warnings)

    found: list[dict[str, object]] = []
    possible: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    seen_missing: dict[str, dict[str, object]] = {}

    for candidate in candidates:
        term = candidate.term
        in_dictionary, entries, match_type = dictionary.lookup(term)
        occurrences, page_set = term_occurrences(term, pages)
        if occurrences == 0:
            # Model, metinde geçmeyen bir ifade döndürdüyse raporlama.
            continue
        base: dict[str, object] = {
            "term": term,
            "found_in_dictionary": in_dictionary,
            "context": find_context(term, pages),
            "pages": sorted(page_set),
            "occurrence_count": occurrences,
        }
        if in_dictionary:
            base["translations"] = list(
                dict.fromkeys(
                    str(entry["tr"])
                    for entry in entries
                    if isinstance(entry.get("tr"), str)
                )
            )
            base["match_type"] = match_type
            found.append(base)
            continue
        if abbreviations is not None:
            abbreviation_entries = abbreviations.lookup(term)
            if abbreviation_entries:
                base["possible_dictionary_terms"] = [
                    {"en": str(entry["expansion"]), "tr": str(entry["turkish"])}
                    for entry in abbreviation_entries
                ]
                base["possible_abbreviation_terms"] = [
                    {
                        "abbreviation": str(entry["abbreviation"]),
                        "expansion": str(entry["expansion"]),
                        "tr": str(entry["turkish"]),
                        "source_page": entry.get("source_page"),
                    }
                    for entry in abbreviation_entries
                ]
                base["match_type"] = "abbreviation_source"
                base["match_source"] = "tbd_abbreviations"
                possible.append(base)
                continue

        # Eksik terimlerde tekil/çoğul tekilleştirmesi (örn. 'downstream task' ve 'downstream tasks')
        sing_key = singular_key(term) or normalized_key(term)
        if sing_key in seen_missing:
            existing = seen_missing[sing_key]
            merged_pages = set(existing.get("pages", [])) | page_set
            existing["pages"] = sorted(merged_pages)
            existing["occurrence_count"] = int(existing.get("occurrence_count", 0)) + occurrences
            # Daha kısa veya tekil olan terim adını koru
            if len(term) < len(str(existing.get("term", ""))):
                existing["term"] = term
                if base["context"]:
                    existing["context"] = base["context"]
        else:
            # Öncelik derecelendirmesi: Çok sözcüklü ve tekrar edenler yüksek öncelik
            words = term.split()
            if len(words) >= 2 or occurrences >= 2:
                base["review_priority"] = "high"
            else:
                base["review_priority"] = "medium"
            seen_missing[sing_key] = base
            missing.append(base)

    found.sort(key=lambda item: str(item["term"]).casefold())
    possible.sort(key=lambda item: str(item["term"]).casefold())
    missing.sort(key=lambda item: str(item["term"]).casefold())

    processed_chunk_count = len(chunks) - len(extraction_warnings)
    if not chunks or processed_chunk_count == 0:
        analysis_status = "failed"
    elif extraction_warnings:
        analysis_status = "partial"
    else:
        analysis_status = "complete"

    return {
        "document": Path(pdf_path).name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "dictionary_version": dictionary.metadata.get("version"),
        "page_count": len(pages),
        "candidate_count": len(candidates),
        "chunk_count": len(chunks),
        "processed_chunk_count": processed_chunk_count,
        "failed_chunk_count": len(extraction_warnings),
        "analysis_status": analysis_status,
        "processing_warnings": extraction_warnings,
        "counts": {
            "dictionary_matches": len(found),
            "possible_matches": len(possible),
            "missing_terms": len(missing),
            "rejected_candidates": 0,
        },
        "dictionary_matches": found,
        "possible_matches": possible,
        "missing_terms": missing,
        "rejected_candidates": [],
    }

