"""V2 uygulama hizmeti: etkin sözlükle analiz ve raporlama."""
from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

from terim_etmeni.ollama_client import OllamaClient
from terim_etmeni.reporting import write_reports

from .abbreviation_index import AbbreviationIndex
from .api_client import ApiClient, ApiClientError
from .config import Settings
from .dictionary_store import DictionaryStatus, DictionaryStore
from .replay import (
    capture_candidate_snapshot,
    replay_snapshot,
    write_candidate_snapshot,
)


class AnalysisBusyError(RuntimeError):
    """Sunucunun eşzamanlı analiz kapasitesi dolu olduğunda yükseltilir."""


class AnalysisService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.dictionaries = DictionaryStore(
            self.settings.dictionary_state_dir,
            self.settings.bootstrap_dictionary,
        )
        self.abbreviations = AbbreviationIndex.load(
            self.settings.bootstrap_abbreviations
        )
        self._analysis_slots = threading.BoundedSemaphore(
            self.settings.max_concurrent_analyses
        )

    def dictionary_status(self) -> DictionaryStatus:
        return self.dictionaries.status()

    def installed_models(self) -> tuple[list[str], str]:
        if self.settings.model_provider == "api":
            if not self.settings.api_base_url or not self.settings.api_key:
                return [], "API ayarları eksik: API_BASE_URL ve API_KEY ortam değişkenleri gerekir."
            return [self.settings.api_model], ""
        try:
            client = OllamaClient(
                self.settings.ollama_url,
                self.settings.model,
                timeout=2,
            )
            return client.installed_models(), ""
        except RuntimeError as error:
            return [], str(error)

    def _api_client(self, model: str) -> ApiClient:
        if not self.settings.api_base_url or not self.settings.api_key:
            raise ApiClientError(
                "API ayarları eksik: API_BASE_URL ve API_KEY ortam değişkenleri gerekir."
            )
        return ApiClient(
            self.settings.api_base_url,
            model,
            self.settings.api_key,
            timeout=self.settings.timeout_seconds,
        )

    def _provider(self, model: str):
        if self.settings.model_provider == "api":
            return self._api_client(model)
        return OllamaClient(
            self.settings.ollama_url,
            model.strip(),
            timeout=self.settings.timeout_seconds,
        )

    def analyze_upload(
        self, filename: str, content: bytes, model: str
    ) -> tuple[dict[str, object], Path, Path, Path]:
        safe_name = Path(filename or "makale.pdf").name
        if not safe_name.casefold().endswith(".pdf") or not content.startswith(b"%PDF-"):
            raise ValueError("Geçerli bir makale PDF'si seçin.")
        if not model.strip():
            raise ValueError("Analiz modeli hazır değil.")
        if not self._analysis_slots.acquire(blocking=False):
            raise AnalysisBusyError(
                "Analiz kapasitesi dolu. Devam eden çalışma bitince yeniden deneyin."
            )

        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as target:
                target.write(content)
                temporary = Path(target.name)
            dictionary = self.dictionaries.load_index()
            client = self._provider(model)
            client.check_model()
            started_at = time.perf_counter()
            snapshot = capture_candidate_snapshot(
                temporary,
                dictionary,
                client,
                model.strip(),
                self.settings.chunk_size,
                self.settings.chunk_overlap,
            )
            snapshot["document"] = safe_name
            result = replay_snapshot(snapshot, dictionary, self.abbreviations)
            result["analysis_duration_seconds"] = round(
                time.perf_counter() - started_at, 3
            )
            result["document"] = safe_name
            status = self.dictionaries.status()
            result["dictionary_source_sha256"] = status.source_sha256
            result["dictionary_record_count"] = status.record_count
            json_path, csv_path = write_reports(result, self.settings.output_dir)
            stem = json_path.name.removesuffix("_terms.json")
            xlsx_path = json_path.parent / "{}_terim_raporu.xlsx".format(stem)
            snapshot_path = json_path.parent / "{}_candidate_snapshot.json".format(stem)
            write_candidate_snapshot(snapshot, snapshot_path)
            return result, json_path, csv_path, xlsx_path
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            self._analysis_slots.release()
