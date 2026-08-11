"""İşlem hattının ortak veri modelleri."""
from __future__ import annotations

from dataclasses import dataclass, field


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
    variants: tuple[str, ...] = ()


@dataclass
class TermEvidence:
    term: str
    pages: set[int] = field(default_factory=set)
    occurrence_count: int = 0
    candidate_sources: set[str] = field(default_factory=set)

    def as_dict(self) -> dict[str, object]:
        return {
            "term": self.term,
            "pages": sorted(self.pages),
            "occurrence_count": self.occurrence_count,
            "candidate_sources": sorted(self.candidate_sources),
        }
