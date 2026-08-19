"""PDF belgelerinden sayfa numarası korunarak metin çıkarımı."""
from __future__ import annotations

import logging
from pathlib import Path
import re

import pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)

from .models import PageText


class PDFReadError(RuntimeError):
    """PDF okunamadığında veya metin katmanı bulunmadığında oluşur."""


# pdfplumber kelime boşluğunu karakterler arası mesafeden tahmin eder; varsayılan
# x_tolerance=3, akademik yayınların sıkı kernli/subset fontlarında boşluğu kaçırıp
# kelimeleri birbirine yapıştırıyordu (ölçüm: örnek makalelerde metnin %2-39'u).
# 1.5'e düşürmek yapışmayı sıfırlarken tek harfli token oranını artırmıyor, yani
# kelimeleri harflerine bölmüyor.
_EXTRACT_OPTIONS = {"x_tolerance": 1.5}

# Sütun tespiti eşikleri: bir aday ayrım çizgisinin üzerinden geçen kelime oranı
# bunun altındaysa ve her iki yanda da en az bu oranda kelime varsa iki sütun kabul edilir.
_MIN_WORDS_FOR_COLUMN_CHECK = 60
_MAX_STRADDLE_RATIO = 0.01
_MIN_COLUMN_SHARE = 0.25


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


_GLUED_RUN = re.compile(r"[^\W\d_]{28,}", re.UNICODE)


def _strip_glued_runs(line: str) -> str:
    """Boşluğu kaybolmuş, birden çok kelimenin bitiştiği harf dizilerini satırdan ayıklar.

    Satırın tamamı bitişikse `_is_low_quality_line` zaten satırı eler; burada ise
    satırın yalnızca bir bölümü bitişik, geri kalanı normal boşluklu olduğu için o
    kontrolün oran eşiğini aşamadığı durumlar hedeflenir (ör. satır sonu tirelemesiyle
    bozulan bir cümle parçasının ardından düzgün bir cümlenin gelmesi).
    """
    return _GLUED_RUN.sub(" ", line)


def clean_extracted_text(text: str) -> str:
    """Yayın üstbilgisi, URL ve kaynakça gürültüsünü ayıklar."""
    cleaned_lines = []
    for line in text.splitlines():
        stripped = _strip_glued_runs(line.strip())
        if _is_low_quality_line(stripped):
            continue
        if re.match(r"^\s*(?:(?:\d+|[IVXLCDM]+)\.?\s*)?(?:references?|bibliography|works cited)(?:\s+(?:and|&)\s+notes)?\s*[-:]?$", stripped, re.IGNORECASE):
            break
        if re.search(r"(?:ISSN|International Journal for Research|©\s*\d{4})", stripped, re.IGNORECASE):
            continue
        stripped = re.sub(r"https?://\S+|www\.\S+", " ", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\b\S+\.(?:com|org|net|edu|gov)(?:/\S*)?", " ", stripped, flags=re.IGNORECASE)
        stripped = " ".join(stripped.split())
        if stripped:
            cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def _find_column_gutter(cropped) -> float | None:
    """İki sütunlu sayfa düzeninde sütunları ayıran boşluğun x konumunu bulur.

    pdfplumber satırları sayfa genişliği boyunca okur; iki sütunlu akademik
    yayınlarda bu, sol sütunun satır sonuyla sağ sütunun satır başını aynı satırda
    birleştirir (ör. ``"... to ana- Alhazmi et al. (2007) define ..."``). Sütunlar
    ayrı ayrı okunursa bu birleşme oluşmaz.

    Aday bir x konumu, sayfanın orta bandında hiçbir kelimenin üzerinden geçmediği
    ve iki yanında da kayda değer miktarda kelime bulunan bir konumdur.
    """
    try:
        words = cropped.extract_words(**_EXTRACT_OPTIONS)
    except Exception:
        return None
    if len(words) < _MIN_WORDS_FOR_COLUMN_CHECK:
        return None

    width = float(cropped.width)
    best: tuple[int, float] | None = None
    for step in range(35, 66):
        split = width * step / 100.0
        straddling = 0
        left = 0
        right = 0
        for word in words:
            if word["x0"] < split < word["x1"]:
                straddling += 1
            elif word["x1"] <= split:
                left += 1
            else:
                right += 1
        if straddling > len(words) * _MAX_STRADDLE_RATIO:
            continue
        if min(left, right) < len(words) * _MIN_COLUMN_SHARE:
            continue
        # En dengeli bölünmeyi seç
        balance = abs(left - right)
        if best is None or balance < best[0]:
            best = (balance, split)
    return None if best is None else best[1]


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
                cropped = page.crop(crop_box)
                gutter = _find_column_gutter(cropped)
                if gutter is None:
                    extracted = cropped.extract_text(**_EXTRACT_OPTIONS) or ""
                else:
                    top, bottom = crop_box[1], crop_box[3]
                    columns = [
                        cropped.crop((0, top, gutter, bottom)),
                        cropped.crop((gutter, top, page.width, bottom)),
                    ]
                    extracted = "\n".join(
                        text
                        for text in (
                            column.extract_text(**_EXTRACT_OPTIONS) or "" for column in columns
                        )
                        if text.strip()
                    )
                extracted = extracted or page.extract_text(**_EXTRACT_OPTIONS) or ""
                cleaned = clean_extracted_text(extracted.strip())
                pages.append(PageText(page=number, text=cleaned))
    except Exception as error:
        raise PDFReadError("PDF okunamadı: {}".format(path.name)) from error

    if not any(page.text for page in pages):
        raise PDFReadError(
            "PDF'de çıkarılabilir metin yok. Taranmış belge için önce OCR uygulanmalı."
        )
    return pages
