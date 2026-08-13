"""V2 komut satırı."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import Settings
from .dictionary_update import check_and_update
from .service import AnalysisService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="turkce-terim-etmeni-v2")
    sub = parser.add_subparsers(dest="command", required=True)
    serve_parser = sub.add_parser("serve", help="V2 web arayüzünü başlat")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8876)
    dictionary = sub.add_parser("dictionary", help="Sözlük durumunu veya güncellemesini yönet")
    dictionary_sub = dictionary.add_subparsers(dest="dictionary_command", required=True)
    dictionary_sub.add_parser("status", help="Etkin sözlüğü göster")
    importer = dictionary_sub.add_parser("import", help="Resmî sözlük PDF'sini doğrula ve etkinleştir")
    importer.add_argument("pdf", type=Path)
    dictionary_sub.add_parser("check", help="TBD sitesinde güncelleme ara")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        from .web_app import serve
        serve(args.host, args.port); return 0
    service = AnalysisService(Settings())
    if args.dictionary_command == "status":
        print(json.dumps(service.dictionary_status().as_dict(), ensure_ascii=False, indent=2)); return 0
    if args.dictionary_command == "import":
        status = service.dictionaries.import_pdf(args.pdf)
        print(json.dumps(status.as_dict(), ensure_ascii=False, indent=2)); return 0
    if args.dictionary_command == "check":
        settings = service.settings
        result = check_and_update(service.dictionaries, page_url=settings.dictionary_page_url, pdf_url=settings.dictionary_pdf_url, timeout=settings.update_timeout_seconds)
        print(result.message); return 0 if result.status != "failed" else 1
    return 2

