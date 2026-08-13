"""V2 uygulama hizmeti: etkin sözlükle analiz ve raporlama."""
from __future__ import annotations

import tempfile
from pathlib import Path

from terim_etmeni.ollama_client import OllamaClient
from terim_etmeni.pipeline import analyze_pdf
from terim_etmeni.reporting import write_reports

from .config import Settings
from .dictionary_store import DictionaryStatus, DictionaryStore


class AnalysisService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.dictionaries = DictionaryStore(
            self.settings.dictionary_state_dir,
            self.settings.bootstrap_dictionary,
        )

    def dictionary_status(self) -> DictionaryStatus:
        return self.dictionaries.status()

    def installed_models(self) -> tuple[list[str], str]:
        try:
            client = OllamaClient(
                self.settings.ollama_url,
                self.settings.model,
                timeout=2,
            )
            return client.installed_models(), ""
        except RuntimeError as error:
            return [], str(error)

    def analyze_upload(
        self, filename: str, content: bytes, model: str
    ) -> tuple[dict[str, object], Path, Path, Path]:
        safe_name = Path(filename or "makale.pdf").name
        if not safe_name.casefold().endswith(".pdf") or not content.startswith(b"%PDF-"):
            raise ValueError("Geçerli bir makale PDF'si seçin.")
        if not model.strip():
            raise ValueError("Analiz modeli hazır değil.")

        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as target:
                target.write(content)
                temporary = Path(target.name)
            dictionary = self.dictionaries.load_index()
            client = OllamaClient(
                self.settings.ollama_url,
                model.strip(),
                timeout=self.settings.timeout_seconds,
            )
            client.check_model()
            result = analyze_pdf(
                temporary,
                dictionary,
                client,
                model.strip(),
                self.settings.chunk_size,
                self.settings.chunk_overlap,
            )
            result["document"] = safe_name
            status = self.dictionaries.status()
            result["dictionary_source_sha256"] = status.source_sha256
            result["dictionary_record_count"] = status.record_count
            json_path, csv_path = write_reports(result, self.settings.output_dir)
            stem = json_path.name.removesuffix("_terms.json")
            xlsx_path = json_path.parent / "{}_terim_raporu.xlsx".format(stem)
            return result, json_path, csv_path, xlsx_path
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

