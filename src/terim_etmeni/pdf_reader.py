"""PDF belgelerinden sayfa numarası korunarak metin çıkarımı."""
from __future__ import annotations

from pathlib import Path
import re

import pdfplumber

from .models import PageText


class PDFReadError(RuntimeError):
    """PDF okunamadığında veya metin katmanı bulunmadığında oluşur."""


def _is_low_quality_line(line: str) -> bool:
    """Bozuk PDF düzeninden gelen formül, kod, şekil ve bitişik metni eler."""
    letters = sum(character.isalpha() for character in line)
    spaces = line.count(" ")
    if letters >= 40 and spaces / letters < 0.06:
        return True
    tokens = line.split()
    if len(tokens) >= 12 and sum(len(token) == 1 for token in tokens) / len(tokens) > 0.35:
        return True
    if re.search(r"(?:\bfig\.?(?:ure)?\s*\d+\b|\beq(?:uation)?\s*\(?\d+\)?\b)", line, re.IGNORECASE):
        return True
    math_symbols = sum(character in "=|∑√≈≤≥𝛼𝛽𝛾𝜎𝜆" for character in line)
    if math_symbols >= 3 and letters < 100:
        return True
    # Kod satırları ve pseudo-code yapılarını temizleme (ör. RASP/Python kod blokları)
    if re.match(r"^\s*\d+\s+(?:def|hist|val|var|let|const|first|same|bal\d*|end_\d*|shuffle_)\b", line):
        return True
    if re.search(r"\b(?:def\s+\w+\(|return\s+|import\s+|from\s+\w+\s+import|selector_width\(|pair_balance\(|frac_prevs\()", line):
        return True
    code_chars = sum(line.count(ch) for ch in ("{", "}", "[", "]", ";", "==", "!=", "=>", "->"))
    if code_chars >= 2 and letters < 80:
        return True
    return False


def clean_extracted_text(text: str) -> str:
    """Yayın üstbilgisi, URL ve kaynakça gürültüsünü ayıklar."""
    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if _is_low_quality_line(stripped):
            continue
        if re.match(r"^\s*(?:references?|bibliography|works cited)\s*[-:]?$", stripped, re.IGNORECASE):
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
            pages = []
            for number, page in enumerate(pdf.pages, start=1):
                # Üstten kırpmayı hafifleterek (0.015) drop-cap harflerin silinmesini önle
                crop_box = (0, page.height * 0.015, page.width, page.height * 0.96)
                extracted = page.crop(crop_box).extract_text() or page.extract_text() or ""
                cleaned = clean_extracted_text(extracted.strip())
                pages.append(PageText(page=number, text=cleaned))
    except Exception as error:
        raise PDFReadError("PDF okunamadı: {}".format(path.name)) from error

    if not any(page.text for page in pages):
        raise PDFReadError(
            "PDF'de çıkarılabilir metin yok. Taranmış belge için önce OCR uygulanmalı."
        )
    return pages
