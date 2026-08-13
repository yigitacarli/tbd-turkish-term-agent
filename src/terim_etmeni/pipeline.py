"""PDF → terim adayları → sözlük karşılaştırması işlem hattı."""
from __future__ import annotations

import re
from collections import OrderedDict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .chunker import chunk_pages
from .config import PROJECT_ROOT
from .dictionary import (
    DictionaryIndex,
    normalized_key,
    relaxed_key,
    singular_key,
    term_tokens,
)
from .models import TermEvidence
from .pdf_reader import read_pdf
from .term_extractor import TermProvider, evidence_for, extract_verified_terms


@lru_cache(maxsize=1)
def _load_common_english_words() -> frozenset[str]:
    """Genel İngilizce kelime listesini yükler (bilişim terimi olmayanlar)."""
    path = PROJECT_ROOT / "data" / "common_english_words.txt"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return frozenset()
    words = set()
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.add(line.casefold())
    return frozenset(words)


_TECHNICAL_COMPOUND_WHITELIST = frozenset({
    "forward process", "reverse process", "score function",
    "score matching", "time step", "noise estimation",
    "sampling method", "image translation",
    "standard normal distribution",
})

def _is_common_english(term: str) -> bool:
    """Terimin tamamen genel İngilizce kelimelerden oluşup oluşmadığını kontrol eder.

    Tek kelimelik terimler doğrudan kontrol edilir.
    Çok kelimelik terimler, tüm kelimeleri genel ise elenir.
    Kısaltmalar (tümü büyük harf) bu filtreden muaftır.
    Bilinen bazı bileşik teknik terimler beyaz liste ile korunur.
    """
    if term.casefold() in _TECHNICAL_COMPOUND_WHITELIST:
        return False
        
    common_words = _load_common_english_words()
    if not common_words:
        return False
    words = term.split()
    # Büyük harfli kısaltmalar (API, TCP vb.) genel kelime değildir
    if len(words) == 1 and words[0].isupper() and len(words[0]) >= 2:
        return False
    return all(w.casefold() in common_words for w in words)


_GENERIC_SINGLE_WORDS = {
    "agriculture",
    "close",
    "decay",
    "dependencies",
    "education",
    "entertainment",
    "histogram",
    "manufacturers",
    "manufacturing",
    "music",
    "purchasing",
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
    r"\b(?:conference on|proceedings of|proc\. of)\b",
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
    "business operations", "commercial equipment", "complementary protection",
    "downstream tasks", "implementation findings", "masked sentence",
    "model architecture", "notification laws",
    "network operators", "technical details", "technical effort",
}

_GEOGRAPHIC_NAMES = {
    "africa", "asia", "europe", "north america", "south america",
    "middle east", "united states",
}

_PROSE_LEADING_WORDS = {
    "accessing", "adopting", "apply", "could", "deploying", "implement",
    "inform", "means", "record", "support", "supports", "whereas",
}

_PROSE_VERB_PATTERN = re.compile(
    r"\b(?:goes|installed|sending|trigger|triggered)\b", re.IGNORECASE
)

_TRUNCATED_WORDS = {
    "arch", "auth", "config", "transac", "implem", "proto",
}

_BENCHMARK_OR_EXPERIMENT_LABELS = {
    "cola", "corr", "glue", "iclr", "mnli", "mrpc", "ppl", "qnli",
    "qqp", "rte", "squad", "sts-b", "swag", "wmt",
}

_LANGUAGE_NAMES = {
    "arabic", "chinese", "dutch", "english", "french", "german", "hindi",
    "italian", "japanese", "korean", "portuguese", "russian", "spanish",
    "turkish",
}

_REFERENCE_CONTEXT_PATTERN = re.compile(
    r"(?:\b(?:proceedings|proc\.|conference|journal|pages?)\b|"
    r"\b(?:19|20)\d{2}\b|\b(?:acl|aaai|corr|iclr|naacl)\b|abs/\d)",
    re.IGNORECASE,
)

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
    if normalized in _GEOGRAPHIC_NAMES:
        return "geographic_name"
    if re.search(
        r"\b(?:january|february|march|april|may|june|july|august|september|"
        r"october|november|december)\s+\d{1,2}(?:,\s*\d{4})?\b",
        normalized,
        re.IGNORECASE,
    ):
        return "date_or_version_label"
    # Ticari model/sürüm isimleri (BERT, GPT-4, GPT-3.5, GPT-4o, ET-BERT, Claude-3 vb.)
    if re.search(
        r"\b(?:gpt(?:[-\s]?[34][o\d\.]*)?|bert(?:[-\s]?[a-z\d]+)?|claude[-\s]?\d*|llama[-\s]?\d*|windows[-\s]?\d+|office[-\s]?\d+)\b",
        term,
        re.IGNORECASE,
    ):
        return "named_product_or_system"
    words = term.split()
    if (
        len(words) >= 2
        and words[-1].casefold() in {"firm", "network", "office", "team"}
        and any(
            word.isupper() or re.match(r"^[A-Z][A-Za-z0-9-]*$", word)
            for word in words[:-1]
        )
    ):
        return "named_group"
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


def _candidate_noise_reason(term: str, pages) -> str | None:
    """Küçük modellerin sık ürettiği biçimsel gürültüyü anlamdan bağımsız eler."""
    words = term.split()
    lowered_words = [word.casefold().strip(".,;:()[]") for word in words]
    lowered = term.casefold()
    if lowered in _BENCHMARK_OR_EXPERIMENT_LABELS:
        return "benchmark_or_experiment_label"
    if any(
        lowered == label + " benchmark"
        for label in _BENCHMARK_OR_EXPERIMENT_LABELS
    ):
        return "benchmark_or_experiment_label"
    language_pair = re.fullmatch(
        r"(?P<left>[A-Z][a-z]+)-(?:to-)?(?P<right>[A-Z][a-z]+)", term
    )
    if (
        language_pair
        and language_pair.group("left").casefold() in _LANGUAGE_NAMES
        and language_pair.group("right").casefold() in _LANGUAGE_NAMES
    ):
        return "language_pair_label"
    if lowered_words and lowered_words[0] in _PROSE_LEADING_WORDS:
        return "prose_fragment"
    if _PROSE_VERB_PATTERN.search(term):
        return "prose_fragment"
    if any(word in _TRUNCATED_WORDS for word in lowered_words):
        return "truncated_pdf_fragment"
    if any(re.search(r"[a-z]{4,}and[a-z]{4,}", word) for word in lowered_words):
        return "compacted_pdf_text"
    if any(left == right for left, right in zip(lowered_words, lowered_words[1:])):
        return "repeated_token_fragment"

    matching_lines = [
        line
        for page in pages
        for line in page.text.splitlines()
        if lowered in line.casefold()
    ]
    if matching_lines and all(_REFERENCE_CONTEXT_PATTERN.search(line) for line in matching_lines):
        return "reference_or_citation_context"

    # PDF satır sonları model isteminde boşluk gibi görünebilir ve iki ayrı
    # başlığı tek bir uzun terime dönüştürebilir. Dört veya daha fazla sözcüklü
    # aday metinde yalnız satır aşarak bulunuyorsa güvenilir bir isim öbeği sayma.
    if len(words) >= 4:
        candidate_tokens = term_tokens(term)
        appears_on_one_line = False
        for page in pages:
            for line in page.text.splitlines():
                tokens = term_tokens(line)
                window = len(candidate_tokens)
                if any(
                    tokens[start : start + window] == candidate_tokens
                    for start in range(max(0, len(tokens) - window + 1))
                ):
                    appears_on_one_line = True
                    break
            if appears_on_one_line:
                break
        if not appears_on_one_line:
            return "cross_line_fragment"
    return None


def _merge_candidate_variants(evidence: list[TermEvidence]) -> list[TermEvidence]:
    """Tire ve son-sözcük çoğulu farklı adayları tek insan kararında toplar."""
    grouped: "OrderedDict[str, list[TermEvidence]]" = OrderedDict()
    for item in evidence:
        grouped.setdefault(singular_key(item.term), []).append(item)

    merged: list[TermEvidence] = []
    for key, variants in grouped.items():
        representative = min(
            variants,
            key=lambda item: (
                relaxed_key(item.term) != key,
                -item.occurrence_count,
                len(item.term),
                item.term.casefold(),
            ),
        )
        combined = TermEvidence(term=representative.term)
        combined.pages = set().union(*(item.pages for item in variants))
        # Varyantların metin eşleşmeleri çakışabileceği için toplam yerine en
        # güçlü kanıtı kullan; böylece çoğul yazım puanı yapay olarak şişirmez.
        combined.occurrence_count = max(item.occurrence_count for item in variants)
        combined.candidate_sources = set().union(
            *(item.candidate_sources for item in variants)
        )
        merged.append(combined)
    return merged


def _canonical_candidate(term: str) -> str:
    candidate = re.sub(
        r"^(?:the|a|an|this|these|those|their|your|our|its|different|multiple|several|various)\s+",
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


def _review_score(item: dict[str, object], model_accepted: bool | None) -> int:
    """Model kararını tek başına veto olarak kullanmadan açıklanabilir puan üretir."""
    sources = set(item.get("candidate_sources", []))
    score = 0
    if "model" in sources:
        score += 3
    if "defined_term" in sources:
        score += 4
    if "technical_pattern" in sources:
        score += 2
    if "quoted_phrase" in sources:
        score += 1
    occurrences = int(item.get("occurrence_count", 0) or 0)
    if occurrences >= 2:
        score += 2
    if occurrences >= 4:
        score += 1
    if len(str(item.get("term", "")).split()) >= 2:
        score += 1
    else:
        score -= 1
        term = str(item.get("term", ""))
        if term[:1].isupper() or term.isupper():
            score += 2
    # Küçük modeller olumlu ikinci turda aşırı kabulcü olabildiği için kabul
    # yanıtı tek başına puan eklemez; ret ise güçlü metin kanıtını veto etmeden
    # yalnız bir basamak güven düşürür.
    if model_accepted is False:
        score -= 1
    return score


def _apply_review_decision(
    item: dict[str, object], model_accepted: bool | None
) -> bool:
    """Adayı puanlar; yalnız anlamlı güven taşıyanları inceleme listesinde tutar."""
    score = _review_score(item, model_accepted)
    item["review_score"] = score
    item["model_review"] = (
        "accepted" if model_accepted is True
        else "rejected" if model_accepted is False
        else "unavailable"
    )
    if score >= 5:
        item["review_priority"] = "high"
        return True
    if score >= 4:
        item["review_priority"] = "medium"
        return True
    item["review_priority"] = "low"
    item["reason"] = "insufficient_review_score"
    return False


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
            noise_reason = _candidate_noise_reason(item.term, pages)
            if noise_reason:
                base["reason"] = noise_reason
                rejected.append(base)
                continue
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
            # Genel İngilizce kelime filtresi: sıradan İngilizce kelimeler
            # (method, approach, result vb.) bilişim terimi değildir.
            if _is_common_english(item.term):
                base["reason"] = "common_english_word"
                rejected.append(base)
                continue
            if _low_confidence_missing(item.term):
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
        "status": (
            "not_available" if not callable(review_method)
            else "complete" if not review_queue
            else "pending"
        ),
    }
    accepted: set[str] | None = None
    if callable(review_method) and review_queue:
        try:
            accepted = {
                normalized_key(term) for term in review_method(
                    [str(item["term"]) for item in review_queue]
                )
            }
        except RuntimeError as error:
            extraction_warnings.append("Teknik terim doğrulaması: {}".format(error))
            technical_review["status"] = "failed"
        else:
            technical_review["status"] = "complete"
            technical_review["accepted_count"] = len(accepted)
            technical_review["accepted_terms"] = [
                str(item["term"])
                for item in review_queue
                if normalized_key(str(item["term"])) in accepted
            ]
    for item in review_queue:
        model_accepted = (
            normalized_key(str(item["term"])) in accepted
            if accepted is not None else None
        )
        if _apply_review_decision(item, model_accepted):
            missing.append(item)
        else:
            rejected.append(item)

    found.sort(key=lambda item: str(item["term"]).casefold())
    possible.sort(key=lambda item: str(item["term"]).casefold())
    missing.sort(
        key=lambda item: (-int(item.get("review_score", 0)), str(item["term"]).casefold())
    )
    rejected.sort(key=lambda item: str(item["term"]).casefold())
    version = dictionary.metadata.get("version")
    if not chunks or processed_chunk_count == 0:
        analysis_status = "failed"
    elif chunk_warning_count or technical_review.get("status") == "failed":
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
