"""Türkçe Terim Etmeni V2 giriş noktası."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from terim_etmeni_v2.cli import main  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("serve")
    raise SystemExit(main())

