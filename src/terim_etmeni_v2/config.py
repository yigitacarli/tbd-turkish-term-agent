"""V2 çalışma zamanı ayarları."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


@dataclass(frozen=True)
class Settings:
    bootstrap_dictionary: Path = PROJECT_ROOT / "data" / "tbd_dictionary_2026_coordinate.json"
    bootstrap_abbreviations: Path = PROJECT_ROOT / "data" / "tbd_abbreviations_2025_03_17.json"
    dictionary_state_dir: Path = PROJECT_ROOT / "data" / "v2_runtime"
    output_dir: Path = PROJECT_ROOT / "output_v2"
    ollama_url: str = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    model: str = os.environ.get("OLLAMA_MODEL", "")
    dictionary_page_url: str = os.environ.get(
        "TBD_DICTIONARY_PAGE_URL",
        "https://bilisimde.ozenliturkce.org.tr/onerilen-tum-terimler-ingilizce-turkce/",
    )
    dictionary_pdf_url: str = os.environ.get("TBD_DICTIONARY_PDF_URL", "")
    chunk_size: int = 6_000
    chunk_overlap: int = 100
    timeout_seconds: int = 240
    update_timeout_seconds: int = 25
    max_concurrent_analyses: int = _positive_int_env("MAX_CONCURRENT_ANALYSES", 1)
