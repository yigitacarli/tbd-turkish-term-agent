"""Resmî TBD kısaltmalar PDF'sini ayrı ve doğrulanmış JSON'a dönüştürür."""
from __future__ import annotations

import re
import time
from collections import defaultdict
from pathlib import Path

import pdfplumber

from .dictionary_pdf import DictionaryImportError, file_sha256


_VERSION_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")
_DECLARED_COUNT_RE = re.compile(r"(?P<count>\d[\d.]*)\s+k.saltma", re.IGNORECASE)
_ENTRY_X_LIMIT = 110.0


def _line_text(words: list[dict[str, object]]) -> str:
    return " ".join(
        str(word["text"])
        for word in sorted(words, key=lambda word: float(word["x0"]))
    ).strip()


def convert_abbreviation_pdf(
    pdf_path: Path,
    *,
    minimum_records: int = 1_000,
    maximum_declared_gap: float = 0.02,
) -> dict[str, object]:
    """Tek sütunlu Excel PDF'sini dönüştürür; şüpheli düzende başarısız olur."""
    path = Path(pdf_path)
    if not path.is_file():
        raise DictionaryImportError("Seçilen dosya geçerli bir PDF değil.")
    with path.open("rb") as source:
        if source.read(5) != b"%PDF-":
            raise DictionaryImportError("Seçilen dosya geçerli bir PDF değil.")

    started = time.monotonic()
    records: list[dict[str, object]] = []
    pending: dict[str, object] | None = None
    version = ""
    declared_count: int | None = None
    page_count = 0

    try:
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            for page_index, page in enumerate(pdf.pages, start=1):
                words = page.extract_words(
                    x_tolerance=1,
                    y_tolerance=2,
                    keep_blank_chars=False,
                    extra_attrs=["fontname", "size"],
                )
                if page_index == 1:
                    first_page_text = " ".join(str(word["text"]) for word in words)
                    version_match = _VERSION_RE.search(first_page_text)
                    version = version_match.group(0) if version_match else ""
                    count_match = _DECLARED_COUNT_RE.search(first_page_text)
                    if count_match:
                        declared_count = int(count_match.group("count").replace(".", ""))

                lines: dict[float, list[dict[str, object]]] = defaultdict(list)
                for word in words:
                    lines[round(float(word["top"]), 1)].append(word)

                for _, line_words in sorted(lines.items()):
                    abbreviation_words = [
                        word
                        for word in line_words
                        if float(word["x0"]) < _ENTRY_X_LIMIT
                        and "Bold" in str(word.get("fontname", ""))
                    ]
                    right_words = [
                        word
                        for word in line_words
                        if float(word["x0"]) >= _ENTRY_X_LIMIT
                    ]
                    if abbreviation_words and right_words:
                        if pending is not None:
                            records.append(pending)
                        pending = {
                            "abbreviation": _line_text(abbreviation_words),
                            "expansion": _line_text(right_words),
                            "turkish": "",
                            "source_page": page_index,
                        }
                    elif pending is not None and right_words:
                        continuation = _line_text(right_words)
                        if continuation:
                            previous = str(pending["turkish"])
                            pending["turkish"] = " ".join(
                                value for value in (previous, continuation) if value
                            )
            if pending is not None:
                records.append(pending)
    except Exception as error:
        if isinstance(error, DictionaryImportError):
            raise
        raise DictionaryImportError(
            "Kısaltmalar PDF'si okunamadı: {}".format(error)
        ) from error

    if not version:
        raise DictionaryImportError("PDF içinde kısaltmalar sürüm tarihi bulunamadı.")
    if declared_count is None:
        raise DictionaryImportError("PDF içinde beyan edilen kısaltma sayısı bulunamadı.")
    if len(records) < minimum_records:
        raise DictionaryImportError(
            "Yalnız {:,} kısaltma kaydı çıkarıldı; PDF düzeni değişmiş olabilir.".format(
                len(records)
            )
        )
    incomplete = [
        record
        for record in records
        if not all(str(record.get(field, "")).strip() for field in ("abbreviation", "expansion", "turkish"))
    ]
    if incomplete:
        raise DictionaryImportError(
            "{} kısaltma satırı eksik okundu; veri etkinleştirilmedi.".format(
                len(incomplete)
            )
        )
    declared_gap = abs(declared_count - len(records)) / declared_count
    if declared_gap > maximum_declared_gap:
        raise DictionaryImportError(
            "PDF {:,} kısaltma beyan ediyor fakat {:,} satır okundu; fark güvenli sınırı aşıyor.".format(
                declared_count, len(records)
            )
        )

    unique_count = len(
        {str(record["abbreviation"]).casefold().strip() for record in records}
    )
    return {
        "metadata": {
            "source": "TBD Bilişim Kısaltmaları Sözlüğü PDF",
            "source_page_url": "https://bilisimde.ozenliturkce.org.tr/tbd-bilisim-kisaltmalari-sozlugu/",
            "source_pdf_url": "https://bilisimde.ozenliturkce.org.tr/docs/TBD-Kisaltmalari-S%C3%B6zl%C3%BC%C4%9F%C3%BC-2025-03-17.pdf",
            "version": version,
            "source_sha256": file_sha256(path),
            "declared_record_count": declared_count,
            "raw_record_count": len(records),
            "declared_record_difference": declared_count - len(records),
            "declared_record_gap_ratio": round(declared_gap, 4),
            "unique_abbreviation_count": unique_count,
            "page_count": page_count,
            "extraction_method": "bold abbreviation coordinate rows",
            "extraction_seconds": round(time.monotonic() - started, 2),
        },
        "abbreviations": records,
    }
