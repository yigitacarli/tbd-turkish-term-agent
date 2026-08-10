"""Sayfa sınırlarını koruyan metin parçalama yardımcıları."""
from __future__ import annotations

import re

from .models import PageText, TextChunk


def _safe_end(text: str, start: int, target: int) -> int:
    """Hedefe yakın bir paragraf, cümle veya sözcük sınırı bulur."""
    if target >= len(text):
        return len(text)
    lower_bound = start + max(1, (target - start) // 2)
    window = text[lower_bound:target]
    candidates = [
        window.rfind("\n\n"),
        max(window.rfind(". "), window.rfind("? "), window.rfind("! ")),
        window.rfind(" "),
    ]
    boundary = next((item for item in candidates if item >= 0), -1)
    return lower_bound + boundary + (2 if boundary >= 0 else len(window))


def chunk_pages(
    pages: list[PageText], size: int = 5_000, overlap: int = 250
) -> list[TextChunk]:
    if size < 200:
        raise ValueError("Parça boyutu en az 200 karakter olmalı.")
    if overlap < 0 or overlap >= size:
        raise ValueError("Örtüşme sıfırdan küçük ve parça boyutundan büyük olamaz.")

    chunks: list[TextChunk] = []
    chunk_index = 0
    for page in pages:
        text = re.sub(r"[ \t]+", " ", page.text).strip()
        start = 0
        while start < len(text):
            end = _safe_end(text, start, min(start + size, len(text)))
            if end <= start:
                end = min(start + size, len(text))
            value = text[start:end].strip()
            if value:
                chunks.append(
                    TextChunk(page=page.page, index=chunk_index, text=value)
                )
                chunk_index += 1
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks

