"""Sabit model adaylarını Ollama çağırmadan V2 filtresinden yeniden geçirir."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from terim_etmeni.dictionary import DictionaryIndex, normalized_key
from terim_etmeni.models import PageText, TermEvidence
from terim_etmeni.chunker import chunk_pages
from terim_etmeni.pdf_reader import read_pdf
from terim_etmeni.pipeline import (
    _acronym_dictionary_match,
    _apply_review_decision,
    _candidate_noise_reason,
    _composite_dictionary_match,
    _expand_model_evidence,
    _is_common_english,
    _low_confidence_missing,
    _merge_candidate_variants,
    _merge_dictionary_evidence,
    _metadata_reason,
    _translations,
)
from terim_etmeni.term_extractor import TermProvider, extract_verified_terms

from .abbreviation_index import AbbreviationIndex


SNAPSHOT_SCHEMA_VERSION = 1
_V2_PROTECTED_TECHNICAL_HEADS = {"transparency"}


class ReplayError(ValueError):
    """Aday anlık görüntüsü güvenle yeniden oynatılamıyorsa üretilir."""


def _is_v2_common_english(term: str) -> bool:
    """Dar teknik başları V1'in genel İngilizce filtresinden korur."""
    words = term.casefold().split()
    if 2 <= len(words) <= 3 and words[-1] in _V2_PROTECTED_TECHNICAL_HEADS:
        return False
    return _is_common_english(term)


def _is_recurring_multiword_phrase(item: dict[str, object]) -> bool:
    """En az iki kez geçen çok sözcüklü öbeği genel İngilizce filtresinden korur.

    ``read lock``, ``write lock``, ``operation log``, ``replication factor``,
    ``distributed transactions`` gibi gerçek teknik terimler sıradan İngilizce
    sözcüklerden oluşur. Bu tür bir öbek teknik metinde tekrar ettiğinde kasıtlı
    bir kavramdır; tekil kullanımlı düz yazı parçası değildir.
    """
    term = str(item.get("term", ""))
    occurrence_count = int(item.get("occurrence_count", 0) or 0)
    return len(term.split()) >= 2 and occurrence_count >= 2


def _is_reviewed_titlecase_technical_pattern(
    item: dict[str, object], model_accepted: bool | None
) -> bool:
    """İki sözcüklü teknik başlığı yalnız sabit olumlu model kararıyla korur."""
    words = str(item.get("term", "")).split()
    sources = set(item.get("candidate_sources", []))
    return (
        model_accepted is True
        and "technical_pattern" in sources
        and len(words) == 2
        and all(word[:1].isupper() for word in words)
    )


def _is_reviewed_acronym_ngram(
    item: dict[str, object], model_accepted: bool | None
) -> bool:
    """Modelce kabul edilen ve açık kısaltma taşıyan düşük puanlı n-gramı korur."""
    words = str(item.get("term", "")).replace("-", " ").split()
    sources = set(item.get("candidate_sources", []))
    has_acronym = any(
        len(word) >= 2 and word.isalpha() and word.isupper() for word in words
    )
    return model_accepted is True and "ngram_scan" in sources and has_acronym


def _is_reviewed_model_plural(
    item: dict[str, object], model_accepted: bool | None
) -> bool:
    """Yalnız model kaynaklı, incelenmiş tek sözcüklü çoğulu korur."""
    term = str(item.get("term", ""))
    sources = set(item.get("candidate_sources", []))
    is_regular_plural = (
        len(term) > 3
        and term.isascii()
        and term.isalpha()
        and term.islower()
        and term.endswith("s")
        and not term.endswith(("ss", "us", "is"))
    )
    return model_accepted is True and sources == {"model"} and is_regular_plural


def _defined_abbreviation_expansion(term: str, pages: Iterable[PageText]) -> str:
    """Belgede `uzun ad (KISALTMA)` biçimindeki en kısa uyumlu açılımı bulur."""
    if not re.fullmatch(r"[A-Z]{2,10}", term):
        return ""
    pattern = re.compile(
        r"(?P<long>(?:[A-Za-z][A-Za-z-]*\s+){0,7}[A-Za-z][A-Za-z-]*)\s*"
        + re.escape("(" + term + ")")
    )
    for page in pages:
        for match in pattern.finditer(page.text):
            words = match.group("long").split()
            for start in range(len(words) - 1, -1, -1):
                phrase = words[start:]
                initials = "".join(
                    part[0]
                    for word in phrase
                    for part in word.split("-")
                    if part
                ).upper()
                if initials == term:
                    return " ".join(phrase)
    return ""


def _abbreviation_source_match(
    term: str,
    pages: Iterable[PageText],
    abbreviations: AbbreviationIndex | None,
) -> tuple[str, list[dict[str, object]]]:
    if abbreviations is None:
        return "", []
    entries = abbreviations.lookup(term)
    if not entries:
        return "", []
    expansion = _defined_abbreviation_expansion(term, pages)
    if expansion:
        defined = abbreviations.lookup_defined(term, expansion)
        if defined:
            return "defined_abbreviation", defined
    return "abbreviation_source", entries


def capture_candidate_snapshot(
    pdf_path: Path,
    dictionary: DictionaryIndex,
    provider: TermProvider,
    model: str,
    chunk_size: int,
    chunk_overlap: int,
) -> dict[str, object]:
    """Tek canlı çıkarımdan replay edilebilir aday ve model-inceleme kararı alır."""
    pages = read_pdf(pdf_path)
    chunks = chunk_pages(pages, size=chunk_size, overlap=chunk_overlap)
    warnings: list[str] = []
    evidence = extract_verified_terms(
        chunks, pages, provider, extraction_warnings=warnings
    )
    snapshot = build_candidate_snapshot(
        document=Path(pdf_path).name,
        model=model,
        pages=pages,
        model_evidence=evidence,
        chunk_count=len(chunks),
        processed_chunk_count=len(chunks) - len(warnings),
        extraction_warnings=warnings,
    )
    review_method = getattr(provider, "validate_terms", None)
    snapshot["technical_review_status"] = (
        "not_available" if not callable(review_method) else "complete"
    )
    if callable(review_method):
        snapshot["technical_review_accepted_terms"] = []
        preliminary = replay_snapshot(snapshot, dictionary)
        review = preliminary.get("technical_review", {})
        candidates = review.get("candidate_terms", []) if isinstance(review, dict) else []
        if isinstance(candidates, list) and candidates:
            try:
                accepted = review_method([str(term) for term in candidates])
            except RuntimeError as error:
                warnings.append("Teknik terim doğrulaması: {}".format(error))
                snapshot["technical_review_status"] = "failed"
                snapshot["technical_review_accepted_terms"] = None
            else:
                snapshot["technical_review_accepted_terms"] = sorted(
                    {str(term) for term in accepted}
                )
    snapshot["processing_warnings"] = warnings
    snapshot["failed_chunk_count"] = len(warnings)
    if any(value.startswith("Teknik terim doğrulaması:") for value in warnings):
        # Teknik doğrulama hatası bir model parçası kaybı değildir.
        snapshot["failed_chunk_count"] = max(0, len(warnings) - 1)
    return snapshot


def build_candidate_snapshot(
    *,
    document: str,
    model: str,
    pages: Iterable[PageText],
    model_evidence: Iterable[TermEvidence],
    chunk_count: int,
    processed_chunk_count: int,
    extraction_warnings: Iterable[str] = (),
    technical_review_accepted_terms: Iterable[str] | None = None,
) -> dict[str, object]:
    """Model çıktısını, kaynak metni ve kanıtı replay için JSON'a dönüştürür."""
    accepted = (
        None
        if technical_review_accepted_terms is None
        else sorted({str(term) for term in technical_review_accepted_terms})
    )
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_type": "candidate_snapshot",
        "document": Path(document).name,
        "model": model,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "pages": [
            {"page": page.page, "text": page.text}
            for page in pages
        ],
        "model_evidence": [item.as_dict() for item in model_evidence],
        "chunk_count": chunk_count,
        "processed_chunk_count": processed_chunk_count,
        "failed_chunk_count": max(0, chunk_count - processed_chunk_count),
        "processing_warnings": list(extraction_warnings),
        "technical_review_accepted_terms": accepted,
        "technical_review_status": (
            "not_available" if accepted is None else "complete"
        ),
    }


def write_candidate_snapshot(snapshot: dict[str, object], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def load_candidate_snapshot(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReplayError("Aday anlık görüntüsü okunamadı: {}".format(error)) from error
    if not isinstance(payload, dict):
        raise ReplayError("Aday anlık görüntüsü bir JSON nesnesi olmalıdır.")
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ReplayError("Aday anlık görüntüsü schema_version değeri 1 olmalıdır.")
    if payload.get("snapshot_type") != "candidate_snapshot":
        raise ReplayError("Dosya bir candidate_snapshot değildir.")
    accepted = payload.get("technical_review_accepted_terms")
    if accepted is not None and not isinstance(accepted, list):
        raise ReplayError("technical_review_accepted_terms liste veya null olmalıdır.")
    _snapshot_pages(payload)
    _snapshot_evidence(payload)
    return payload


def _snapshot_pages(snapshot: dict[str, object]) -> list[PageText]:
    raw_pages = snapshot.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        raise ReplayError("Aday anlık görüntüsünde kaynak sayfalar bulunmalıdır.")
    pages: list[PageText] = []
    for raw in raw_pages:
        if not isinstance(raw, dict):
            raise ReplayError("Geçersiz kaynak sayfa kaydı.")
        page = raw.get("page")
        text = raw.get("text")
        if not isinstance(page, int) or page <= 0 or not isinstance(text, str):
            raise ReplayError("Geçersiz kaynak sayfa kaydı.")
        pages.append(PageText(page=page, text=text))
    return pages


def _snapshot_evidence(snapshot: dict[str, object]) -> list[TermEvidence]:
    raw_items = snapshot.get("model_evidence")
    if not isinstance(raw_items, list):
        raise ReplayError("Aday anlık görüntüsünde model_evidence listesi gerekir.")
    evidence: list[TermEvidence] = []
    for raw in raw_items:
        if not isinstance(raw, dict) or not str(raw.get("term", "")).strip():
            raise ReplayError("Geçersiz model kanıtı kaydı.")
        pages = raw.get("pages", [])
        sources = raw.get("candidate_sources", [])
        if not isinstance(pages, list) or not isinstance(sources, list):
            raise ReplayError("Geçersiz model kanıtı kaydı.")
        evidence.append(
            TermEvidence(
                term=str(raw["term"]),
                pages={int(page) for page in pages},
                occurrence_count=int(raw.get("occurrence_count", 0)),
                candidate_sources={str(source) for source in sources},
            )
        )
    return evidence


def replay_snapshot(
    snapshot: dict[str, object],
    dictionary: DictionaryIndex,
    abbreviations: AbbreviationIndex | None = None,
) -> dict[str, object]:
    """Sabit adayları mevcut deterministik sözlük/filtre politikasıyla sınıflar."""
    pages = _snapshot_pages(snapshot)
    evidence = _expand_model_evidence(_snapshot_evidence(snapshot), pages, dictionary)
    evidence = _merge_candidate_variants(evidence)
    evidence = _merge_dictionary_evidence(evidence, pages, dictionary)

    found: list[dict[str, object]] = []
    possible: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    review_queue: list[dict[str, object]] = []
    for item in evidence:
        status, entries = dictionary.lookup(item.term)
        base = item.as_dict()
        if status in {"exact", "possible"}:
            base["translations"] = _translations(entries)
            if status == "possible":
                base["possible_dictionary_terms"] = [
                    {"en": entry["en"], "tr": entry["tr"]}
                    for entry in entries
                    if isinstance(entry.get("en"), str)
                    and isinstance(entry.get("tr"), str)
                ]
                base["match_type"] = "normalized_variant"
            found.append(base)
            continue
        reason = _candidate_noise_reason(item.term, pages)
        if reason:
            base["reason"] = reason
            rejected.append(base)
            continue
        acronym_entries = _acronym_dictionary_match(item.term, pages, dictionary)
        if acronym_entries:
            base["possible_dictionary_terms"] = [
                {"en": entry["en"], "tr": entry["tr"]}
                for entry in acronym_entries
                if isinstance(entry.get("en"), str)
                and isinstance(entry.get("tr"), str)
            ]
            base["match_type"] = "defined_abbreviation"
            possible.append(base)
            continue
        abbreviation_match_type, abbreviation_entries = _abbreviation_source_match(
            item.term, pages, abbreviations
        )
        if abbreviation_entries:
            base["possible_dictionary_terms"] = [
                {
                    "en": str(entry["expansion"]),
                    "tr": str(entry["turkish"]),
                }
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
            base["match_type"] = abbreviation_match_type
            base["match_source"] = "tbd_abbreviations"
            possible.append(base)
            continue
        if _composite_dictionary_match(item.term, dictionary):
            continue
        reason = _metadata_reason(item.term)
        if reason:
            base["reason"] = reason
            rejected.append(base)
            continue
        if _is_v2_common_english(item.term) and not _is_recurring_multiword_phrase(base):
            base["reason"] = "common_english_word"
            rejected.append(base)
            continue
        if _low_confidence_missing(item.term):
            base["reason"] = "low_confidence_phrase"
            rejected.append(base)
            continue
        review_queue.append(base)

    accepted_raw = snapshot.get("technical_review_accepted_terms")
    accepted = (
        None
        if accepted_raw is None
        else {normalized_key(str(term)) for term in accepted_raw}
    )
    for item in review_queue:
        model_accepted = (
            None
            if accepted is None
            else normalized_key(str(item["term"])) in accepted
        )
        accepted_by_score = _apply_review_decision(item, model_accepted)
        rescued_by_v2_policy = (
            _is_reviewed_titlecase_technical_pattern(item, model_accepted)
            or _is_reviewed_acronym_ngram(item, model_accepted)
            or _is_reviewed_model_plural(item, model_accepted)
        )
        if not accepted_by_score and rescued_by_v2_policy:
            item.pop("reason", None)
            item["review_priority"] = "medium"
            accepted_by_score = True
        if accepted_by_score:
            missing.append(item)
        else:
            rejected.append(item)

    found.sort(key=lambda item: str(item["term"]).casefold())
    possible.sort(key=lambda item: str(item["term"]).casefold())
    missing.sort(
        key=lambda item: (-int(item.get("review_score", 0)), str(item["term"]).casefold())
    )
    rejected.sort(key=lambda item: str(item["term"]).casefold())
    warnings = snapshot.get("processing_warnings", [])
    failed_chunks = int(snapshot.get("failed_chunk_count", 0) or 0)
    processed_chunks = int(snapshot.get("processed_chunk_count", 0) or 0)
    technical_snapshot_status = str(
        snapshot.get("technical_review_status", "not_available")
    )
    analysis_status = (
        "failed" if processed_chunks == 0
        else "partial" if failed_chunks or technical_snapshot_status == "failed"
        else "complete"
    )
    technical_status = (
        "failed" if technical_snapshot_status == "failed"
        else "not_available" if accepted is None
        else "replayed"
    )
    return {
        "document": str(snapshot.get("document", "document.pdf")),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": str(snapshot.get("model", "")),
        "dictionary_version": dictionary.metadata.get("version"),
        "abbreviation_source": (
            {
                "name": "TBD Bilişim Kısaltmaları Sözlüğü",
                "version": abbreviations.metadata.get("version"),
                "source_sha256": abbreviations.metadata.get("source_sha256"),
                "record_count": abbreviations.metadata.get("raw_record_count"),
                "unique_abbreviation_count": abbreviations.metadata.get(
                    "unique_abbreviation_count"
                ),
            }
            if abbreviations is not None
            else None
        ),
        "page_count": len(pages),
        "verified_candidate_count": len(evidence),
        "chunk_count": int(snapshot.get("chunk_count", 0) or 0),
        "processed_chunk_count": processed_chunks,
        "failed_chunk_count": failed_chunks,
        "analysis_status": analysis_status,
        "processing_warnings": warnings if isinstance(warnings, list) else [],
        "replay": {
            "enabled": True,
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "ollama_called": False,
        },
        "technical_review": {
            "enabled": accepted is not None,
            "candidate_count": len(review_queue),
            "accepted_count": (
                len([item for item in review_queue if normalized_key(str(item["term"])) in accepted])
                if accepted is not None else len(review_queue)
            ),
            "candidate_terms": [str(item["term"]) for item in review_queue],
            "accepted_terms": (
                [str(item["term"]) for item in review_queue if normalized_key(str(item["term"])) in accepted]
                if accepted is not None else [str(item["term"]) for item in review_queue]
            ),
            "status": technical_status,
        },
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
