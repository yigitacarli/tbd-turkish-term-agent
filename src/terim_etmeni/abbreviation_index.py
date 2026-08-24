"""Ana terim sözlüğünden ayrı TBD kısaltma dizini."""
from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from terim_etmeni.dictionary import relaxed_key


class AbbreviationFormatError(RuntimeError):
    pass


def abbreviation_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    return " ".join(value.split())


def abbreviation_surface(value: str) -> str:
    """Kısaltmanın yazımını (büyük/küçük harf) koruyan karşılaştırma biçimi."""
    return " ".join(unicodedata.normalize("NFKC", value).strip().split())


class AbbreviationIndex:
    def __init__(self, entries: Iterable[dict[str, object]], metadata=None) -> None:
        self.metadata = metadata or {}
        self._entries: dict[str, list[dict[str, object]]] = defaultdict(list)
        for raw_entry in entries:
            abbreviation = raw_entry.get("abbreviation")
            expansion = raw_entry.get("expansion")
            turkish = raw_entry.get("turkish")
            if not all(isinstance(value, str) and value.strip() for value in (abbreviation, expansion, turkish)):
                continue
            self._entries[abbreviation_key(abbreviation)].append(dict(raw_entry))

    @classmethod
    def load(cls, path: Path) -> "AbbreviationIndex":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise AbbreviationFormatError(
                "Kısaltma dizini okunamadı: {}".format(path)
            ) from error
        if not isinstance(data, dict) or not isinstance(data.get("abbreviations"), list):
            raise AbbreviationFormatError(
                "Kısaltma dizininde 'abbreviations' listesi bulunamadı."
            )
        return cls(data["abbreviations"], metadata=data.get("metadata", {}))

    def lookup(self, abbreviation: str) -> list[dict[str, object]]:
        return list(self._entries.get(abbreviation_key(abbreviation), []))

    def lookup_written_form(self, abbreviation: str) -> list[dict[str, object]]:
        """Yalnız kısaltmanın kayıtlı yazımıyla birebir eşleşen kayıtları döndürür.

        ``lookup`` büyük/küçük harfe duyarsızdır; bu, metindeki sıradan bir
        sözcüğün (``set``, ``art``, ``as``) aynı harfleri taşıyan bir TBD
        kısaltmasıyla (``SET``, ``ART``, ``AS``) eşleşip incelenmesi gereken
        bir terimi kısaltma grubuna düşürmesine yol açıyordu (ADR-049).

        Yazıma duyarlı eşleşme ``RAM`` → ``RAM`` ve ``AIoT`` → ``AIoT`` gibi
        gerçek kısaltmaları korur; kayıtlı yazımı zaten küçük harf olan
        ``aux`` gibi maddeler de küçük harfle eşleşmeye devam eder.
        """
        expected = abbreviation_surface(abbreviation)
        return [
            entry
            for entry in self._entries.get(abbreviation_key(abbreviation), [])
            if abbreviation_surface(str(entry["abbreviation"])) == expected
        ]

    def lookup_defined(
        self, abbreviation: str, expansion: str
    ) -> list[dict[str, object]]:
        expected = relaxed_key(expansion)
        return [
            entry
            for entry in self.lookup(abbreviation)
            if relaxed_key(str(entry["expansion"])) == expected
        ]

    def __len__(self) -> int:
        return len(self._entries)
