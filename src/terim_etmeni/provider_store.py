"""Arayüzden girilen bulut API ayarlarını yerel dosyada saklayan depo.

API anahtarı yalnızca kullanıcının kendi bilgisayarındaki bu dosyada durur;
Git'e eklenmez (``data/runtime/`` zaten ``.gitignore`` içindedir). Sağlayıcı,
adres ve model bilgisi de aynı dosyadadır; böylece kullanıcı ortam değişkeniyle
uğraşmadan arayüzden kendi API'sini tanımlayabilir.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .api_client import provider_base_url, provider_default_model


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    api_key: str
    model: str
    base_url: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
        }


def _normalize_provider(value: str) -> str:
    return value.strip().casefold() or "openai"


def _env_config() -> ProviderConfig:
    """Ortam değişkenlerinden sağlayıcı ayarı okur; ``.env`` ile çalıştırmayı sağlar."""
    return ProviderConfig(
        provider=_normalize_provider(os.environ.get("API_PROVIDER", "openai")),
        api_key=os.environ.get("API_KEY", ""),
        model=os.environ.get("API_MODEL", ""),
        base_url=os.environ.get("API_BASE_URL", ""),
    )


class ProviderConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> ProviderConfig:
        if not self.path.is_file():
            return _env_config()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _env_config()
        if not isinstance(data, dict):
            return _env_config()
        provider = _normalize_provider(str(data.get("provider", "openai")))
        config = ProviderConfig(
            provider=provider,
            api_key=str(data.get("api_key", "")),
            model=str(data.get("model", "")),
            base_url=str(data.get("base_url", "")),
        )
        # Dosyada anahtar yoksa ortam değişkenine düş; env anahtar verdiğinde
        # sağlayıcıyı da env belirler.
        if not config.api_key:
            env = _env_config()
            return ProviderConfig(
                provider=env.provider if env.api_key else config.provider,
                api_key=env.api_key,
                model=config.model or env.model,
                base_url=config.base_url or env.base_url,
            )
        return config

    def save(self, config: ProviderConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".provider-", suffix=".tmp", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as target:
                json.dump(config.as_dict(), target, ensure_ascii=False, indent=2)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def resolved(self, settings_model: str = "") -> ProviderConfig:
        config = self.load()
        model = config.model or settings_model
        return ProviderConfig(
            provider=config.provider,
            api_key=config.api_key,
            model=model or provider_default_model(config.provider),
            base_url=config.base_url or provider_base_url(config.provider),
        )
