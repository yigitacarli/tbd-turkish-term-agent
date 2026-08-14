"""Uygulama hizmeti: etkin sözlükle analiz ve raporlama."""
from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path

from terim_etmeni.ollama_client import OllamaClient
from terim_etmeni.reporting import write_reports

from .abbreviation_index import AbbreviationIndex
from .api_client import ApiClient, ApiClientError, provider_base_url
from .config import Settings
from .dictionary_store import DictionaryStatus, DictionaryStore
from .pipeline import TermDictionary, analyze_pdf
from .provider_store import ProviderConfig, ProviderConfigStore


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
        self.provider_config = ProviderConfigStore(
            self.settings.provider_config_file
        )
        self._analysis_slots = threading.BoundedSemaphore(
            self.settings.max_concurrent_analyses
        )

    @property
    def provider_store(self) -> ProviderConfigStore:
        return self.provider_config

    def dictionary_status(self) -> DictionaryStatus:
        return self.dictionaries.status()

    def save_provider_config(self, config: ProviderConfig) -> None:
        self.provider_config.save(config)

    def provider_status(self) -> dict[str, str]:
        config = self.provider_config.load()
        return {
            "provider": config.provider,
            "model": config.model,
            "base_url": config.base_url or provider_base_url(config.provider),
            "custom_base_url": config.base_url if config.base_url != provider_base_url(config.provider) else "",
            "has_key": bool(config.api_key),
        }

    def _resolved_api(self) -> ProviderConfig:
        config = self.provider_config.resolved(self.settings.api_model)
        # Eğer kayıtlı base_url başka bir sağlayıcıya aitse, onu temizle ve geçerli sağlayıcının adresini kullan
        provider = config.provider
        base_url = config.base_url
        if provider == "google" and "deepseek" in base_url:
            base_url = provider_base_url("google")
        elif provider == "deepseek" and "googleapis" in base_url:
            base_url = provider_base_url("deepseek")
        elif provider == "openai" and ("deepseek" in base_url or "googleapis" in base_url or "anthropic" in base_url):
            base_url = provider_base_url("openai")
        elif provider == "anthropic" and ("deepseek" in base_url or "googleapis" in base_url or "openai" in base_url):
            base_url = provider_base_url("anthropic")
        return ProviderConfig(
            provider=provider,
            api_key=config.api_key,
            model=config.model,
            base_url=base_url,
        )


    def using_api(self) -> bool:
        """Sağlayıcıyı seçer: açık ortam ayarı, yoksa kayıtlı API anahtarı."""
        choice = self.settings.model_provider.casefold()
        if choice == "api":
            return True
        if choice == "ollama":
            return False
        config = self._resolved_api()
        if config.provider == "ollama":
            return False
        return bool(config.api_key)

    def installed_models(self) -> tuple[list[str], str]:
        if self.using_api():
            config = self._resolved_api()
            if not config.api_key:
                return [], "API anahtarı ayarlanmamış. Ayarlar sayfasından girin."
            return [config.model], ""
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
        config = self._resolved_api()
        if not config.api_key:
            raise ApiClientError("API anahtarı ayarlanmamış. Ayarlar sayfasından girin.")
        if model and model != config.model:
            config = ProviderConfig(
                provider=config.provider,
                api_key=config.api_key,
                model=model,
                base_url=config.base_url,
            )
        return ApiClient(
            config.provider,
            config.api_key,
            config.model,
            base_url=config.base_url,
            timeout=self.settings.timeout_seconds,
        )

    def _provider(self, model: str):
        if self.using_api():
            return self._api_client(model)
        return OllamaClient(
            self.settings.ollama_url,
            model.strip(),
            timeout=self.settings.timeout_seconds,
        )

    def _dictionary(self) -> TermDictionary:
        terms, metadata = self.dictionaries.load_terms()
        return TermDictionary(terms, metadata=metadata)

    def _analyze(
        self, pdf_path: Path, model: str, display_name: str
    ) -> tuple[dict[str, object], Path, Path, Path]:
        dictionary = self._dictionary()
        client = self._provider(model)
        client.check_model()
        model_name = str(getattr(client, "model", "") or model.strip())
        started_at = time.perf_counter()
        result = analyze_pdf(
            pdf_path,
            dictionary,
            client,
            model_name,
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            abbreviations=self.abbreviations,
        )
        result["analysis_duration_seconds"] = round(
            time.perf_counter() - started_at, 3
        )
        result["document"] = display_name
        status = self.dictionaries.status()
        result["dictionary_source_sha256"] = status.source_sha256
        result["dictionary_record_count"] = status.record_count
        if result.get("analysis_status") == "failed":
            return result, Path(""), Path(""), Path("")
        json_path, csv_path = write_reports(result, self.settings.output_dir)
        stem = json_path.name.removesuffix("_terms.json")
        xlsx_path = json_path.parent / "{}_terim_raporu.xlsx".format(stem)
        return result, json_path, csv_path, xlsx_path


    def analyze_upload(
        self, filename: str, content: bytes, model: str
    ) -> tuple[dict[str, object], Path, Path, Path]:
        safe_name = Path(filename or "makale.pdf").name
        if not safe_name.casefold().endswith(".pdf") or not content.startswith(b"%PDF-"):
            raise ValueError("Geçerli bir makale PDF'si seçin.")
        if not self.using_api() and not model.strip():
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
            return self._analyze(temporary, model, safe_name)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            self._analysis_slots.release()

    def analyze_path(
        self, pdf_path: Path, model: str
    ) -> tuple[dict[str, object], Path, Path, Path]:
        if not self.using_api() and not model.strip():
            raise ValueError("Analiz modeli hazır değil.")
        path = Path(pdf_path)
        if not path.is_file():
            raise ValueError("PDF bulunamadı: {}".format(path))
        return self._analyze(path, model, path.name)
