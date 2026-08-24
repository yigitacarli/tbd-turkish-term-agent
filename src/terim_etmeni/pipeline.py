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
    document_acronyms,
    extract_terms_from_chunks,
    find_context,
    locate_term,
)


from terim_etmeni.dictionary import (
    condensed_key,
    normalized_key,
    relaxed_key,
    singular_key,
    term_tokens,
    _singular_token,
)


def _is_bare_acronym(name: object) -> bool:
    """Yalın kısaltma biçimi mi? ('MLM' evet, 'masked LM' hayır.)"""
    text = str(name).strip()
    return (
        bool(text)
        and len(text) <= 10
        and text.isupper()
        and any(c.isalpha() for c in text)
    )


def _priority_score(term: str, occurrences: int) -> int:
    """Eksik terimin inceleme sırası puanı (ADR-044).

    Deterministiktir ve yalnızca sunumu belirler: hiçbir aday elenmez.
    - Çok sözcüklü başlıklar +2 (bağımsız sözlük maddesi olma eğilimi)
    - Tek sözcük -1 (bağlam denetimi gerektirme eğilimi; yasak değil)
    - Belge içi sıklık: 2 geçiş +1, 3+ geçiş +2
    """
    score = 0
    if len(term.split()) >= 2:
        score += 2
    else:
        score -= 1
    if occurrences >= 3:
        score += 2
    elif occurrences == 2:
        score += 1
    return score


def _missing_concept_keys(
    term: str, pairs: dict[str, str], reverse_pairs: dict[str, str]
) -> list[str]:
    """Eksik adayın kavram anahtarları (ADR-032 + ADR-042).

    Sırayla: tekil/çoğul anahtarı, ayraç duyarsız sıkıştırılmış anahtarı ve
    belge içinde tanımlıysa kısaltma ↔ açılım karşılığının anahtarları.
    Farklı sözcük dizileri asla aynı anahtara düşmez.
    """
    sing = singular_key(term) or normalized_key(term)
    keys = [sing] if sing else []
    cond = condensed_key(term)
    if cond and cond not in keys:
        keys.append(cond)
    norm_term = normalized_key(term)
    long_form = pairs.get(norm_term)
    if long_form:
        long_sing = singular_key(long_form) or long_form
        for extra in (long_sing, condensed_key(long_form)):
            if extra and extra not in keys:
                keys.append(extra)
    else:
        acronym = reverse_pairs.get(norm_term)
        if acronym:
            acro_key = normalized_key(acronym)
            if acro_key and acro_key not in keys:
                keys.append(acro_key)
    return keys


class TermDictionary:
    """Normalize edilmiş İngilizce terimler üzerinden deterministik sözlük."""

    def __init__(self, terms: list[dict[str, object]], metadata: dict | None = None) -> None:
        self.metadata = metadata or {}
        self._exact: dict[str, list[dict[str, object]]] = {}
        self._relaxed: dict[str, list[dict[str, object]]] = {}
        self._singular: dict[str, list[dict[str, object]]] = {}
        # 2-6 sözcüklük başlıklar için belirteç dizisi indeksi; belge metninde
        # modelin önermediği kayıtlı terimleri bulan süpürmede kullanılır (ADR-045).
        self._phrases: dict[tuple[str, ...], list[dict[str, object]]] = {}
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
                words = term_tokens(english)
                if 2 <= len(words) <= 6:
                    self._phrases.setdefault(words, []).append(item)

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

    def sweep_phrases(self, pages) -> dict[str, dict[str, object]]:
        """Metinde geçen kayıtlı çok sözcüklü başlıkları doğrudan bulur (ADR-045).

        Modelden bağımsız deterministik taramadır: yalnızca doğrulanmış
        sözlükteki 2-6 sözcüklük başlıklar, kesin/tekil-çoğul eşleşmeyle
        aranır. Dönen değer: normalize edilmiş terim -> bilgi sözlüğü.
        """
        hits: dict[str, dict[str, object]] = {}
        for page in pages:
            tokens = term_tokens(page.text)
            for start in range(len(tokens)):
                max_length = min(6, len(tokens) - start)
                for length in range(2, max_length + 1):
                    window = tokens[start : start + length]
                    entries = self._phrases.get(window)
                    observed = None
                    if not entries:
                        singular_window = window[:-1] + (
                            _singular_token(window[-1]),
                        )
                        if singular_window != window:
                            entries = self._phrases.get(singular_window)
                            if entries:
                                observed = " ".join(window)
                    if not entries:
                        continue
                    # Kayıt, gözlenen yüzey biçimiyle değil sözlük başlığının
                    # kanonik anahtarıyla tutulur; aksi hâlde tekil/çoğul
                    # yüzeyler ayrı satırlar üretir.
                    english = str(entries[0]["en"])
                    canon_key = normalized_key(english)
                    info = hits.setdefault(
                        canon_key,
                        {"term": english, "count": 0, "pages": set()},
                    )
                    info["count"] = int(info["count"]) + 1
                    info["pages"].add(page.page)
        return {
            key: {"term": info["term"], "count": int(info["count"]),
                  "pages": sorted(info["pages"])}
            for key, info in hits.items()
        }



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
    # Belge içinde açıkça tanımlanan kısaltma ↔ açılım çiftleri; eksik
    # terimlerin kavram bazında birleştirilmesinde kullanılır (ADR-042).
    acronym_pairs = document_acronyms(pages)
    reverse_pairs = {long_form: short for short, long_form in acronym_pairs.items()}
    extraction_warnings: list[str] = []
    candidates = extract_terms_from_chunks(chunks, extractor, extraction_warnings)

    found: list[dict[str, object]] = []
    possible: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    seen_missing: dict[str, dict[str, object]] = {}
    seen_found: dict[str, dict[str, object]] = {}

    for candidate in candidates:
        term = candidate.term
        in_dictionary, entries, match_type = dictionary.lookup(term)
        occurrences, page_set, found_form = locate_term(term, pages)
        if occurrences == 0:
            # Model, metinde hiçbir yüzey biçimiyle geçmeyen bir ifade döndürdü
            # (uydurma veya açılım). Rapordan çıkarılır ama izlenebilir kalsın diye kaydedilir.
            rejected.append({"term": term, "reason": "not_found_in_text"})
            continue
        base: dict[str, object] = {
            "term": term,
            "found_in_dictionary": in_dictionary,
            "context": find_context(found_form, pages),
            "pages": sorted(page_set),
            "occurrence_count": occurrences,
        }
        if found_form != term:
            # Metinde terimin kendisi değil bir çekim/tireli biçimi geçiyor; hangi
            # biçim üzerinden sayıldığı denetlenebilir olsun.
            base["matched_form"] = found_form
        if in_dictionary:
            base["translations"] = list(
                dict.fromkeys(
                    str(entry["tr"])
                    for entry in entries
                    if isinstance(entry.get("tr"), str)
                )
            )
            base["match_type"] = match_type
            # Tek sözcüklü eşleşmelerde sözlükteki karşılık makaledeki anlamla
            # örtüşmeyebilir ('attention' → 'uyarı'). Terim gizlenmez, yalnızca
            # raporda bağlam denetimi gerektiği işaretlenir (ADR-041).
            if len(term.split()) == 1:
                base["context_check_needed"] = True
            # Tekil/çoğul aynı sözlük girdisine düşüyorsa tek satırda birleştir
            # (örn. 'vulnerability' ve 'vulnerabilities' ayrı ayrı raporlanmasın).
            found_key = singular_key(term) or normalized_key(term)
            existing_found = seen_found.get(found_key)
            if existing_found is not None:
                existing_found["pages"] = sorted(set(existing_found.get("pages", [])) | page_set)
                existing_found["occurrence_count"] = (
                    int(existing_found.get("occurrence_count", 0)) + occurrences
                )
                if match_type == "exact" and existing_found.get("match_type") != "exact":
                    existing_found["term"] = term
                    existing_found["match_type"] = match_type
                    if base["context"]:
                        existing_found["context"] = base["context"]
                continue
            seen_found[found_key] = base
            found.append(base)
            continue
        if abbreviations is not None:
            abbreviation_entries = abbreviations.lookup_written_form(term)
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

        # Eksik terim tekilleştirmesi (ADR-032 + ADR-042): tekil/çoğul,
        # tire/boşluk yazımı ve belge içinde tanımlı kısaltma ↔ açılım
        # çiftleri tek kavramda birleşir. Hiçbir yüzey biçimi gizlenmez;
        # birleşen adlar 'variants' alanında rapora yazılır.
        concept_keys = _missing_concept_keys(term, acronym_pairs, reverse_pairs)
        existing = None
        for key in concept_keys:
            if key in seen_missing:
                existing = seen_missing[key]
                break
        if existing is not None:
            merged_pages = set(existing.get("pages", [])) | page_set
            existing["pages"] = sorted(merged_pages)
            existing["occurrence_count"] = int(existing.get("occurrence_count", 0)) + occurrences
            # Daha kısa veya tekil olan terim adını koru
            canonical = str(existing.get("term", ""))
            variant_name = term
            if len(variant_name) < len(canonical):
                canonical, variant_name = variant_name, canonical
            # Yalın kısaltma yerine açık biçim görünsün ('MLM' değil
            # 'masked language model'); kısaltma 'variants'a taşınır.
            if _is_bare_acronym(canonical) and not _is_bare_acronym(variant_name):
                canonical, variant_name = variant_name, canonical
            if canonical != existing["term"]:
                existing["term"] = canonical
                if base["context"]:
                    existing["context"] = base["context"]
            variants = [str(v) for v in (existing.get("variants") or [])]
            if variant_name != canonical and variant_name not in variants:
                variants.append(variant_name)
            if variants:
                existing["variants"] = sorted(dict.fromkeys(variants))
            if not str(existing.get("context") or "").strip() and base["context"]:
                existing["context"] = base["context"]
            for key in concept_keys:
                seen_missing[key] = existing
        else:
            # Öncelik puanı (ADR-044): sunum amaçlı sıralamadır, eleme değildir.
            # Çok sözcüklük ve belge içi sıklık yükseltir; tek sözcük düşürür.
            score = _priority_score(term, occurrences)
            if score >= 2:
                base["review_priority"] = "high"
            elif score == 1:
                base["review_priority"] = "medium"
            else:
                base["review_priority"] = "low"
            base["priority_score"] = score
            for key in concept_keys:
                seen_missing[key] = base
            missing.append(base)

    # Deterministik sözlük süpürmesi (ADR-045): modelin önermediği kayıtlı
    # çok sözcüklü başlıklar belge metninden bulunup sözlük eşleşmelerine
    # eklenir. Yalnızca doğrulanmış sözlükle kesin eşleşme; halüsinasyon
    # riski yoktur ve hiçbir model adayı silinmez.
    reported_norm = {
        normalized_key(str(item.get("term", "")))
        for collection in (found, possible, missing, rejected)
        for item in collection
        if isinstance(item, dict) and str(item.get("term", "")).strip()
    }
    for key, info in sorted(dictionary.sweep_phrases(pages).items()):
        if key in reported_norm:
            continue
        _, entries, _match_type = dictionary.lookup(info["term"])
        sweep_entry: dict[str, object] = {
            "term": info["term"],
            "found_in_dictionary": True,
            "context": find_context(info["term"], pages),
            "pages": info["pages"],
            "occurrence_count": info["count"],
            "match_type": "exact",
            "match_source": "dictionary_sweep",
            "translations": list(
                dict.fromkeys(
                    str(entry["tr"])
                    for entry in entries
                    if isinstance(entry.get("tr"), str)
                )
            ),
        }
        seen_found[key] = sweep_entry
        found.append(sweep_entry)

    found.sort(key=lambda item: str(item["term"]).casefold())
    possible.sort(key=lambda item: str(item["term"]).casefold())
    # Eksik terimler öncelik puanına göre dizilir; uzman listeye baştan
    # girer. Hiçbir terim listeden çıkarılmaz.
    missing.sort(
        key=lambda item: (
            -int(item.get("priority_score", 0)),
            str(item["term"]).casefold(),
        )
    )

    processed_chunk_count = len(chunks) - len(extraction_warnings)
    if not chunks or processed_chunk_count == 0:
        analysis_status = "failed"
    elif extraction_warnings:
        analysis_status = "partial"
    else:
        analysis_status = "complete"

    # Parçalar hatasız işlendiği hâlde model hiç aday döndürmediyse sonuç teknik
    # olarak başarılıdır ama boş rapor "belgede eksik terim yok" diye okunmamalıdır.
    # Durum kodu değişmez (analiz gerçekten tamamlandı); uyarı kayda geçer.
    report_warnings = list(extraction_warnings)
    if chunks and processed_chunk_count and not candidates:
        report_warnings.append(
            "Model {} parçanın tamamını işledi ancak hiç terim adayı döndürmedi; "
            "bu sonuç “belgede eksik terim yok” anlamına gelmez.".format(
                processed_chunk_count
            )
        )

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
        "processing_warnings": report_warnings,
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

