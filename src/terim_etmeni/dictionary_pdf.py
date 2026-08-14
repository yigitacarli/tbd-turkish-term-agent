"""TBD'nin iki sütunlu sözlük PDF'sini doğrulanmış JSON'a dönüştürme."""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

import pdfplumber


class DictionaryImportError(RuntimeError):
    pass


_VERSION_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _cell_text(words: list[dict[str, object]]) -> str:
    ordered = sorted(words, key=lambda word: (round(float(word["top"]), 1), float(word["x0"])))
    return " ".join(str(word["text"]) for word in ordered).strip()


def convert_dictionary_pdf(
    pdf_path: Path,
    *,
    minimum_records: int = 1_000,
    previous_record_count: int | None = None,
) -> dict[str, object]:
    """PDF'yi dönüştürür; şüpheli sonuçlarda kullanılabilir veri döndürmez."""
    path = Path(pdf_path)
    if not path.is_file():
        raise DictionaryImportError("Seçilen dosya geçerli bir PDF değil.")
    with path.open("rb") as source:
        header = source.read(5)
    if header != b"%PDF-":
        raise DictionaryImportError("Seçilen dosya geçerli bir PDF değil.")

    started = time.monotonic()
    terms: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    version = ""
    page_count = 0
    separator_count = 0

    try:
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            for page_index, page in enumerate(pdf.pages, start=1):
                words = page.extract_words(
                    x_tolerance=1,
                    y_tolerance=2,
                    keep_blank_chars=False,
                )
                if page_index == 1:
                    first_page_text = " ".join(str(word["text"]) for word in words)
                    match = _VERSION_RE.search(first_page_text)
                    version = match.group(0) if match else ""

                # Kaynak PDF Excel'den üretilir. İngilizce ve Türkçe sütunları
                # arasındaki ':' ayırıcısı sayfalarda yaklaşık x=278 konumundadır.
                separators = [
                    word
                    for word in words
                    if word["text"] == ":"
                    and 275 <= float(word["x0"]) <= 282
                    and (page_index > 1 or float(word["top"]) > 290)
                ]
                separators.sort(key=lambda word: float(word["top"]))
                separator_count += len(separators)

                for position, separator in enumerate(separators):
                    top = float(separator["top"])
                    lower = (
                        (float(separators[position - 1]["top"]) + top) / 2
                        if position
                        else top - 7
                    )
                    upper = (
                        (top + float(separators[position + 1]["top"])) / 2
                        if position + 1 < len(separators)
                        else top + 7
                    )
                    row_words = [
                        word
                        for word in words
                        if word is not separator and lower <= float(word["top"]) < upper
                    ]
                    english = _cell_text(
                        [word for word in row_words if float(word["x1"]) < 277]
                    )
                    turkish = _cell_text(
                        [word for word in row_words if float(word["x0"]) > 282]
                    )
                    if english and turkish:
                        terms.append(
                            {"en": english, "tr": turkish, "source_page": page_index}
                        )
                    else:
                        skipped.append(
                            {
                                "source_page": page_index,
                                "english": english,
                                "turkish": turkish,
                            }
                        )
    except Exception as error:
        if isinstance(error, DictionaryImportError):
            raise
        raise DictionaryImportError("Sözlük PDF'si okunamadı: {}".format(error)) from error

    if not version:
        raise DictionaryImportError("PDF içinde sözlük sürüm tarihi bulunamadı.")
    if len(terms) < minimum_records:
        raise DictionaryImportError(
            "Yalnız {:,} kayıt çıkarıldı; sözlük düzeni değişmiş olabilir.".format(len(terms))
        )
    if separator_count and len(skipped) / separator_count > 0.01:
        raise DictionaryImportError(
            "Satırların yüzde birinden fazlası okunamadı; eski sözlük korunuyor."
        )
    if previous_record_count and len(terms) < int(previous_record_count * 0.85):
        raise DictionaryImportError(
            "Yeni sözlük önceki sürümden yüzde 15'ten fazla küçük; otomatik etkinleştirilmedi."
        )

    unique_count = len({str(item["en"]).casefold().strip() for item in terms})
    return {
        "metadata": {
            "source": "TBD Bilişimde Özenli Türkçe sözlüğü PDF",
            "version": version,
            "source_sha256": file_sha256(path),
            "raw_record_count": len(terms),
            "unique_english_term_count": unique_count,
            "page_count": page_count,
            "separator_candidates": separator_count,
            "skipped_separator_candidates": len(skipped),
            "extraction_method": "coordinate table separator",
            "extraction_seconds": round(time.monotonic() - started, 2),
        },
        "terms": terms,
    }
