"""Varsayılan yollar ve çalışma zamanı ayarları."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    dictionary_path: Path = PROJECT_ROOT / "data" / "tbd_dictionary_2026_coordinate.json"
    output_dir: Path = PROJECT_ROOT / "output"
    ollama_url: str = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    model: str = os.environ.get("OLLAMA_MODEL", "qwen3.5:2b")
    chunk_size: int = 6_000
    chunk_overlap: int = 100
    timeout_seconds: int = 240
