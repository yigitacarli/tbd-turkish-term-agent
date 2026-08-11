"""PDF → terim adayları → sözlük karşılaştırması işlem hattı."""
from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from .chunker import chunk_pages
from .dictionary import DictionaryIndex, normalized_key, relaxed_key, term_tokens
from .models import TermEvidence
from .pdf_reader import read_pdf
from .term_extractor import TermProvider, evidence_for, extract_verified_terms


_GENERIC_SINGLE_WORDS = {
    "agriculture",
    "close",
    "decay",
    "dependencies",
    "education",
    "entertainment",
    "histogram",
    "music",
    "selector",
    "seq",
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

_METADATA_PATTERNS = (
    r"\b(?:author|orcid|copyright|licensing|how to cite)\b",
    r"\b(?:technical series|white papers?|publication|publication identifier|policies)\b",
    r"\b(?:national institute|information technology laboratory)\b",
)

_ORGANIZATION_PATTERNS = (
    r"\b(?:corporation|technologies|laboratory|institute)\b$",
    r"^(?:nist|nccoe)(?:\b|\s)",
)

_GENERIC_COMPOSITE_SUFFIXES = {
    # "cloud security capabilities" gibi ifadelerde son sözcük, teknik
    # çekirdeğe yeni bir kavram katmaz. Buna karşılık "architecture",
    # "protocol" veya "standard" gibi ekler bağımsız teknik anlam
    # taşıyabileceğinden burada genelleştirilmez ve doğrulama aşamasına kalır.
    "capabilities",
    "technology",
}

_NAMED_PRODUCT_HEADS = {
    "bot", "platform", "software", "system", "systems", "volumes",
}

_GENERIC_MISSING_PHRASES = {
    "commercial equipment", "complementary protection", "implementation findings",
    "network operators", "technical details", "technical effort",
}

# Genel başlıkları (ör. "Knowledge Base System") kişi adı sanmamak için yalnızca
# yaygın verilen adlarla başlayan kısa baş harfli diziler elenir.
_GIVEN_NAMES = {
    "aarin", "andrew", "anna", "brian", "dan", "david", "don", "erica", "gary", "james",
    "jeffrey", "john", "jorge", "karen", "mark", "michael", "murugiah", "paul",
    "rajasekhar", "robert", "sophia", "susan", "thomas", "william",
}


def _is_title_cased_person_name(term: str) -> bool:
    """Kısa, tümü baş harfli kişi adlarını eksik terim listesinden çıkarır."""
    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", term)
    return (
        2 <= len(words) <= 4
        and words[0].casefold() in _GIVEN_NAMES
        and all(re.fullmatch(r"[A-Z][a-z]+(?:[A-Z][a-z]+)*", word) for word in words)
        and not any(character.isdigit() for character in term)
    )


def _metadata_reason(term: str) -> str | None:
    """Künye, kurum veya kişi adı olan model adaylarını sınıflandırır."""
    normalized = normalized_key(term)
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _METADATA_PATTERNS):
        return "publication_metadata"
    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _ORGANIZATION_PATTERNS):
        return "organization_or_institution"
    if _is_title_cased_person_name(term):
        return "person_name"
    # Ticari model/sürüm isimleri (GPT-4, GPT-3.5, GPT-4o, ET-BERT, Claude-3 vb.)
    if re.search(
        r"\b(?:gpt[-\s]?[34][o\d\.]*|bert[-\s]?[a-z\d]+|claude[-\s]?\d*|llama[-\s]?\d*|windows[-\s]?\d+|office[-\s]?\d+)\b",
        term,
        re.IGNORECASE,
    ):
        return "named_product_or_system"
    words = term.split()
    if (
        len(words) == 1
        and re.fullmatch(r"[A-Z][a-z]+", words[0])
        and words[0].casefold() in _GIVEN_NAMES
    ):
        return "person_name"
    if len(words) >= 2 and words[-1].casefold() in _NAMED_PRODUCT_HEADS:
        leading = words[:-1]
        title_cased_product = (
            words[-1].casefold() not in {"system", "systems"}
            and all(re.match(r"^[A-Z]", word) for word in words)
        )
        if any(word.isupper() and len(word) >= 2 for word in leading) or title_cased_product:
            return "named_product_or_system"
    if normalized in _GENERIC_MISSING_PHRASES:
        return "generic_phrase"
    return None


def _composite_dictionary_match(
    term: str, dictionary: DictionaryIndex
) -> list[dict[str, object]]:
    """Kök sözlük terimine eklenen genel son ekleri olası eşleşme sayar."""
    candidate = term_tokens(term)
    if len(candidate) < 2:
        return []
    for base_length in range(len(candidate) - 1, 0, -1):
        base = candidate[:base_length]
        suffix = candidate[len(base) :]
        if suffix and all(token in _GENERIC_COMPOSITE_SUFFIXES for token in suffix):
            status, entries = dictionary.lookup(" ".join(base))
            if status != "missing":
                return entries
    return []


def _acronym_dictionary_match(
    term: str, pages, dictionary: DictionaryIndex
) -> list[dict[str, object]]:
    """Parantezde tanımlanan kısaltmayı ana terimin sözlük kaydıyla eşleştirir."""
    if not re.fullmatch(r"[A-Z]{2,10}", term):
        return []
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
                if initials != term:
                    continue
                status, entries = dictionary.lookup(" ".join(phrase))
                if status != "missing":
                    return entries
    return []


def _low_confidence_missing(term: str) -> bool:
    words = term.split()
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
    candidate = re.sub(
        r"^(?:the|a|an|this|these|those|their|our|its|different|multiple|several|various)\s+",
        "",
        term,
        flags=re.IGNORECASE,
    ).strip()
    # Çoğul kısaltmaları tekilleştirme (LLMs -> LLM, RNNs -> RNN, GANs -> GAN)
    if re.fullmatch(r"[A-Z]{2,10}s", candidate):
        candidate = candidate[:-1]
    # Parantezde verilen kısaltma sözlük teriminin parçası değildir:
    # ``Knowledge-Based Systems(KBS)`` önce ana terimle karşılaştırılır.
    candidate = re.sub(
        r"\s*\([A-Z][A-Z0-9/-]{1,14}\)\s*$", "", candidate
    ).strip()
    # Sayı içeren teknoloji adlarında genel "systems/technology" uzantısı yeni
    # bir terim değildir; kök ad altında tek adayda toplanır.
    match = re.fullmatch(
        r"([A-Za-z]*\d+[A-Za-z\d]*)[-\s]+(?:architecture components|systems|technology|enabled technology)",
        candidate,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else candidate


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
                split_evidence = [
                    evidence_for(left, pages, item.candidate_sources),
                    evidence_for(right, pages, item.candidate_sources),
                ]
                if all(value.occurrence_count for value in split_evidence):
                    expanded.extend(split_evidence)
                    continue
        if candidate != item.term:
            item = evidence_for(candidate, pages, item.candidate_sources)
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
    extraction_warnings: list[str] = []
    model_evidence = extract_verified_terms(
        chunks, pages, provider, extraction_warnings=extraction_warnings
    )
    chunk_warning_count = len(extraction_warnings)
    processed_chunk_count = len(chunks) - chunk_warning_count
    evidence = _expand_model_evidence(model_evidence, pages, dictionary)
    evidence = _merge_dictionary_evidence(evidence, pages, dictionary)

    found: list[dict[str, object]] = []
    possible: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    review_queue: list[dict[str, object]] = []
    for item in evidence:
        status, entries = dictionary.lookup(item.term)
        base = item.as_dict()
        if status == "exact":
            base["translations"] = _translations(entries)
            found.append(base)
        elif status == "possible":
            # Büyük/küçük harf, tire ve düzenli son sözcük çoğulu yeni bir
            # kavram oluşturmaz. Bunları inceleme kuyruğunu şişirmek yerine
            # sözlük tarafından kapsanan kontrollü biçim değişkeleri sayarız.
            base["translations"] = _translations(entries)
            base["possible_dictionary_terms"] = [
                {"en": entry["en"], "tr": entry["tr"]}
                for entry in entries
                if isinstance(entry.get("en"), str)
                and isinstance(entry.get("tr"), str)
            ]
            base["match_type"] = "normalized_variant"
            found.append(base)
        else:
            entries = _acronym_dictionary_match(item.term, pages, dictionary)
            if entries:
                base["possible_dictionary_terms"] = [
                    {"en": entry["en"], "tr": entry["tr"]}
                    for entry in entries
                    if isinstance(entry.get("en"), str)
                    and isinstance(entry.get("tr"), str)
                ]
                base["match_type"] = "defined_abbreviation"
                possible.append(base)
                continue
            entries = _composite_dictionary_match(item.term, dictionary)
            if entries:
                # "cloud security capabilities" gibi bir ifade, sözlükteki
                # teknik çekirdeğe eklenmiş cümle bağlamıdır. Kök terim zaten
                # metin içi sözlük taramasında bulunur; genişletilmiş ifadeyi
                # ikinci bir aday olarak göstermeyiz.
                continue
            metadata_reason = _metadata_reason(item.term)
            if metadata_reason:
                base["reason"] = metadata_reason
                rejected.append(base)
                continue
            if len(item.term.split()) == 1:
                # Tek sözcük ve kısaltmaların gürültü olma olasılığı daha
                # yüksektir; yine de gerçek yeni terimleri kaybetmemek için
                # sessizce elemek yerine düşük öncelikli incelemeye alırız.
                base["review_priority"] = "low"
                base["reason"] = "single_word_review"
                review_queue.append(base)
            elif (
                "model" not in item.candidate_sources
                and item.candidate_sources
                & {
                    "defined_term", "technical_pattern", "repeated_abbreviation",
                    "quoted_phrase",
                }
            ):
                # Modelin hiç önermediği fakat kontrollü bir deterministik
                # sinyalle bulunan aday sessizce kaybolmaz. Gürültü riskinden
                # dolayı düşük öncelikli insan incelemesinde tutulur.
                base["review_priority"] = "low"
                base["reason"] = "deterministic_recovery"
                review_queue.append(base)
            elif _low_confidence_missing(item.term):
                base["reason"] = "low_confidence_phrase"
                rejected.append(base)
            else:
                review_queue.append(base)

    review_method = getattr(provider, "validate_terms", None)
    technical_review = {
        "enabled": callable(review_method),
        "candidate_count": len(review_queue),
        "accepted_count": len(review_queue),
        "candidate_terms": [str(item["term"]) for item in review_queue],
        "accepted_terms": [str(item["term"]) for item in review_queue],
    }
    if callable(review_method) and review_queue:
        try:
            accepted = {
                normalized_key(term) for term in review_method(
                    [str(item["term"]) for item in review_queue]
                )
            }
        except RuntimeError as error:
            extraction_warnings.append("Teknik terim doğrulaması: {}".format(error))
        else:
            technical_review["accepted_count"] = len(accepted)
            technical_review["accepted_terms"] = [
                str(item["term"])
                for item in review_queue
                if normalized_key(str(item["term"])) in accepted
            ]
            for item in review_queue:
                model_accepted = normalized_key(str(item["term"])) in accepted
                if model_accepted or item.get("review_priority") == "low":
                    if not model_accepted:
                        item["model_review"] = "rejected_but_retained_for_human_review"
                    missing.append(item)
                else:
                    item["reason"] = "non_technical_contextual_phrase"
                    rejected.append(item)
            review_queue = []
    missing.extend(review_queue)

    found.sort(key=lambda item: str(item["term"]).casefold())
    possible.sort(key=lambda item: str(item["term"]).casefold())
    missing.sort(key=lambda item: str(item["term"]).casefold())
    rejected.sort(key=lambda item: str(item["term"]).casefold())
    version = dictionary.metadata.get("version")
    if not chunks or processed_chunk_count == 0:
        analysis_status = "failed"
    elif chunk_warning_count:
        analysis_status = "partial"
    else:
        analysis_status = "complete"
    return {
        "document": Path(pdf_path).name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "dictionary_version": version,
        "page_count": len(pages),
        "verified_candidate_count": len(evidence),
        "chunk_count": len(chunks),
        "processed_chunk_count": processed_chunk_count,
        "failed_chunk_count": chunk_warning_count,
        "analysis_status": analysis_status,
        "processing_warnings": extraction_warnings,
        "technical_review": technical_review,
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
