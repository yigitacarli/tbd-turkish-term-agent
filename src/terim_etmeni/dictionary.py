"""İngilizce → Türkçe sözlüğü yükleme ve deterministik eşleştirme."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable


_DASHES = "‐‑‒–—−"


def normalized_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    return " ".join(value.split())


def relaxed_key(value: str) -> str:
    value = normalized_key(value)
    value = re.sub("[{}\\-]+".format(_DASHES), " ", value)
    return " ".join(value.split())


def singular_key(value: str) -> str:
    """Yalnızca son İngilizce sözcükte temkinli bir çoğul normalizasyonu yapar."""
    words = relaxed_key(value).split()
    if not words:
        return ""
    word = words[-1]
    if len(word) > 4 and word.endswith("ies"):
        word = word[:-3] + "y"
    elif len(word) > 4 and word.endswith(("ches", "shes", "sses", "xes", "zes")):
        word = word[:-2]
    elif len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    words[-1] = word
    return " ".join(words)


def term_tokens(value: str) -> tuple[str, ...]:
    value = unicodedata.normalize("NFKC", value).casefold()
    return tuple(re.findall(r"[^\W_]+|[+#]+", value, flags=re.UNICODE))


def _singular_token(value: str) -> str:
    if len(value) > 4 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 4 and value.endswith(("ches", "shes", "sses", "xes", "zes")):
        return value[:-2]
    if len(value) > 3 and value.endswith("s") and not value.endswith(("ss", "us", "is")):
        return value[:-1]
    return value


class DictionaryFormatError(RuntimeError):
    pass


class DictionaryIndex:
    def __init__(self, entries: Iterable[dict[str, object]], metadata=None) -> None:
        self.metadata = metadata or {}
        self._exact: dict[str, list[dict[str, object]]] = defaultdict(list)
        self._relaxed: dict[str, list[dict[str, object]]] = defaultdict(list)
        self._phrases: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
        for raw_entry in entries:
            english = raw_entry.get("en")
            turkish = raw_entry.get("tr")
            if not isinstance(english, str) or not isinstance(turkish, str):
                continue
            entry = dict(raw_entry)
            self._exact[normalized_key(english)].append(entry)
            self._relaxed[relaxed_key(english)].append(entry)
            tokens = term_tokens(english)
            if 2 <= len(tokens) <= 6:
                self._phrases[tokens].append(entry)

    @classmethod
    def load(cls, path: Path) -> "DictionaryIndex":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DictionaryFormatError("Sözlük okunamadı: {}".format(path)) from error
        if not isinstance(data, dict) or not isinstance(data.get("terms"), list):
            raise DictionaryFormatError("Sözlükte 'terms' listesi bulunamadı.")
        return cls(data["terms"], metadata=data.get("metadata", {}))

    def lookup(self, term: str) -> tuple[str, list[dict[str, object]]]:
        exact = self._exact.get(normalized_key(term), [])
        if exact:
            return "exact", list(exact)
        possible = self._relaxed.get(relaxed_key(term), [])
        if possible:
            return "possible", list(possible)
        singular = self._relaxed.get(singular_key(term), [])
        if singular:
            return "possible", list(singular)
        return "missing", []

    def __len__(self) -> int:
        return len(self._exact)

    def find_phrases(self, text: str) -> list[tuple[str, int]]:
        """Metinde geçen 2-6 sözcüklük sözlük terimlerini doğrudan bulur."""
        tokens = term_tokens(text)
        hits: dict[str, tuple[str, int]] = {}
        for start in range(len(tokens)):
            for length in range(2, min(6, len(tokens) - start) + 1):
                window = tokens[start : start + length]
                entries = self._phrases.get(window)
                observed = None
                if not entries:
                    singular_window = window[:-1] + (_singular_token(window[-1]),)
                    if singular_window != window:
                        entries = self._phrases.get(singular_window)
                        if entries:
                            observed = " ".join(window)
                if not entries:
                    continue
                english = observed or str(entries[0]["en"])
                key = normalized_key(english)
                previous = hits.get(key)
                hits[key] = (english, (previous[1] if previous else 0) + 1)
        return sorted(hits.values(), key=lambda item: item[0].casefold())
