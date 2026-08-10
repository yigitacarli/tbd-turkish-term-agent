"""PDF belgelerinden sayfa numarası korunarak metin çıkarımı."""
from __future__ import annotations

from pathlib import Path
import re

import pdfplumber

from .models import PageText


class PDFReadError(RuntimeError):
    """PDF okunamadığında veya metin katmanı bulunmadığında oluşur."""


def clean_extracted_text(text: str) -> str:
    """Yayın üstbilgisi, URL ve kaynakça gürültüsünü ayıklar."""
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"(?:references|bibliography)\s*[-:]?", stripped, re.IGNORECASE):
            break
        if re.search(r"(?:ISSN|International Journal for Research|©\s*\d{4})", stripped, re.IGNORECASE):
            continue
        stripped = re.sub(r"https?://\S+|www\.\S+", " ", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\b\S+\.(?:com|org|net|edu|gov)(?:/\S*)?", " ", stripped, flags=re.IGNORECASE)
        stripped = " ".join(stripped.split())
        if stripped:
            cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def read_pdf(path: Path) -> list[PageText]:
    path = Path(path)
    if not path.is_file():
        raise PDFReadError("PDF bulunamadı: {}".format(path))
    if path.suffix.casefold() != ".pdf":
        raise PDFReadError("Desteklenmeyen dosya türü: {}".format(path.name))

    try:
        with pdfplumber.open(path) as pdf:
            pages = [
                PageText(
                    page=number,
                    text=clean_extracted_text(
                        (
                            page.crop(
                            (0, page.height * 0.04, page.width, page.height * 0.95)
                            ).extract_text()
                            or ""
                        ).strip()
                    ),
                )
                for number, page in enumerate(pdf.pages, start=1)
            ]
    except Exception as error:
        raise PDFReadError("PDF okunamadı: {}".format(path.name)) from error

    if not any(page.text for page in pages):
        raise PDFReadError(
            "PDF'de çıkarılabilir metin yok. Taranmış belge için önce OCR uygulanmalı."
        )
    return pages
