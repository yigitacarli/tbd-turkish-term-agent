"""İşlem hattının ortak veri modelleri."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageText:
    page: int
    text: str


@dataclass(frozen=True)
class TextChunk:
    page: int
    index: int
    text: str


@dataclass(frozen=True)
class ExtractedTerm:
    term: str
