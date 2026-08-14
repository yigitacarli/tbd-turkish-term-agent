"""Etkin sözlüğü sürümleyen ve son sağlam sürümü koruyan depo."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from terim_etmeni.dictionary import DictionaryFormatError, DictionaryIndex

from .dictionary_pdf import DictionaryImportError, convert_dictionary_pdf


@dataclass(frozen=True)
class DictionaryStatus:
    path: Path
    version: str
    record_count: int
    unique_count: int
    source_sha256: str
    activated_at: str
    source: str
    managed: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "version": self.version,
            "record_count": self.record_count,
            "unique_count": self.unique_count,
            "source_sha256": self.source_sha256,
            "activated_at": self.activated_at,
            "source": self.source,
            "managed": self.managed,
        }


class DictionaryStore:
    def __init__(self, state_dir: Path, bootstrap_path: Path) -> None:
        self.state_dir = Path(state_dir)
        self.bootstrap_path = Path(bootstrap_path)
        self.active_file = self.state_dir / "active.json"

    def _read_data(self, path: Path) -> dict[str, object]:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DictionaryImportError("Sözlük JSON'u okunamadı: {}".format(path)) from error
        if not isinstance(data, dict) or not isinstance(data.get("terms"), list):
            raise DictionaryImportError("Sözlük JSON'unda 'terms' listesi bulunamadı.")
        return data

    def active_path(self) -> Path:
        if self.active_file.is_file():
            try:
                state = json.loads(self.active_file.read_text(encoding="utf-8"))
                candidate = (self.state_dir / str(state["filename"])).resolve()
                if candidate.parent == self.state_dir.resolve() and candidate.is_file():
                    return candidate
            except (OSError, KeyError, json.JSONDecodeError):
                pass
        return self.bootstrap_path

    def status(self) -> DictionaryStatus:
        path = self.active_path()
        data = self._read_data(path)
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        terms = data["terms"]
        unique = metadata.get("unique_english_term_count")
        if not isinstance(unique, int):
            unique = len(
                {
                    str(item.get("en", "")).casefold().strip()
                    for item in terms
                    if isinstance(item, dict) and item.get("en")
                }
            )
        return DictionaryStatus(
            path=path,
            version=str(metadata.get("version", "bilinmiyor")),
            record_count=len(terms),
            unique_count=unique,
            source_sha256=str(metadata.get("source_sha256", "")),
            activated_at=str(metadata.get("activated_at", "")),
            source=str(metadata.get("source", "Yerel başlangıç sözlüğü")),
            managed=path != self.bootstrap_path,
        )

    def load_index(self) -> DictionaryIndex:
        try:
            return DictionaryIndex.load(self.active_path())
        except DictionaryFormatError as error:
            raise DictionaryImportError(str(error)) from error

    def load_terms(self) -> tuple[list[dict[str, object]], dict[str, object]]:
        """Etkin sözlüğün ham terimlerini ve metadata'sını döndürür."""
        data = self._read_data(self.active_path())
        metadata = data.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        terms = data["terms"]
        if not isinstance(terms, list):
            raise DictionaryImportError("Sözlük JSON'unda 'terms' listesi bulunamadı.")
        return terms, metadata

    def import_pdf(self, pdf_path: Path) -> DictionaryStatus:
        previous = self.status()
        data = convert_dictionary_pdf(
            Path(pdf_path), previous_record_count=previous.record_count
        )
        metadata = data["metadata"]
        assert isinstance(metadata, dict)
        digest = str(metadata["source_sha256"])
        if previous.source_sha256 and digest == previous.source_sha256:
            return previous

        metadata["activated_at"] = datetime.now(timezone.utc).isoformat()
        version = str(metadata["version"])
        filename = "dictionary-{}-{}.json".format(version, digest[:12])
        self.state_dir.mkdir(parents=True, exist_ok=True)
        destination = self.state_dir / filename
        self._atomic_json(destination, data)

        # Yazılan JSON gerçekten yüklenebiliyor mu? İşaretçi ancak bundan sonra değişir.
        try:
            DictionaryIndex.load(destination)
        except DictionaryFormatError as error:
            raise DictionaryImportError("Yeni sözlük doğrulanamadı: {}".format(error)) from error
        self._atomic_json(
            self.active_file,
            {"filename": filename, "activated_at": metadata["activated_at"]},
        )
        return self.status()

    def _atomic_json(self, path: Path, data: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".{}-".format(path.name), suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as target:
                json.dump(data, target, ensure_ascii=False, indent=2)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

