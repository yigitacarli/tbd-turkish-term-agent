"""Komut satırı."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .abbreviation_pdf import convert_abbreviation_pdf
from .config import Settings
from .dictionary_update import check_and_update
from .expected_evaluation import (
    ExpectedEvaluationError,
    evaluate_expected,
    format_expected,
    load_expected,
)
from .service import AnalysisService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="turkce-terim-etmeni")
    sub = parser.add_subparsers(dest="command", required=True)
    serve_parser = sub.add_parser("serve", help="Web arayüzünü başlat")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8876)
    serve_parser.add_argument(
        "--no-browser", action="store_true", help="Tarayıcıyı otomatik açma"
    )
    scan = sub.add_parser("scan", help="Tek bir PDF'yi analiz et ve raporla")
    scan.add_argument("pdf", type=Path)
    scan.add_argument(
        "--model",
        default="",
        help="Kullanılacak model. Ollama için zorunlu; API sağlayıcısı için isteğe bağlı.",
    )
    dictionary = sub.add_parser("dictionary", help="Sözlük durumunu veya güncellemesini yönet")
    dictionary_sub = dictionary.add_subparsers(dest="dictionary_command", required=True)
    dictionary_sub.add_parser("status", help="Etkin sözlüğü göster")
    importer = dictionary_sub.add_parser("import", help="Resmî sözlük PDF'sini doğrula ve etkinleştir")
    importer.add_argument("pdf", type=Path)
    dictionary_sub.add_parser("check", help="TBD sitesinde güncelleme ara")
    abbreviations = sub.add_parser(
        "abbreviations", help="Ayrı TBD kısaltma kaynağını incele veya dönüştür"
    )
    abbreviation_sub = abbreviations.add_subparsers(
        dest="abbreviation_command", required=True
    )
    abbreviation_sub.add_parser("status", help="Etkin kısaltma kaynağını göster")
    abbreviation_convert = abbreviation_sub.add_parser(
        "convert", help="Resmî kısaltmalar PDF'sini doğrulanmış JSON'a dönüştür"
    )
    abbreviation_convert.add_argument("pdf", type=Path)
    abbreviation_convert.add_argument("--output", type=Path, required=True)
    expected = sub.add_parser(
        "evaluate-expected",
        help="Bir raporu makale bazlı beklenen eksik-terim listesiyle ölç",
    )
    expected.add_argument("expected", type=Path)
    expected.add_argument("result", type=Path)
    expected.add_argument("--output", type=Path, help="Ölçümü JSON olarak yaz")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        from .web_app import serve, validate_bind_host
        try:
            host = validate_bind_host(args.host)
        except ValueError as error:
            parser.error(str(error))
        serve(host, args.port, open_browser=not args.no_browser); return 0
    if args.command == "scan":
        from terim_etmeni.reporting import format_terminal_report

        service = AnalysisService(Settings())
        model = args.model or service.settings.model
        try:
            result, json_path, csv_path, _ = service.analyze_path(args.pdf, model)
        except Exception as error:
            parser.error(str(error))
        print(format_terminal_report(result))
        print("JSON raporu: {}".format(json_path))
        print("CSV raporu: {}".format(csv_path))
        return 0
    if args.command == "evaluate-expected":
        try:
            expected_terms = load_expected(args.expected)
            report = json.loads(Path(args.result).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ExpectedEvaluationError) as error:
            parser.error(str(error))
        result = evaluate_expected(expected_terms, report)
        print(format_expected(result))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print("JSON ölçüm özeti: {}".format(args.output))
        return 0
    if args.command == "abbreviations" and args.abbreviation_command == "convert":
        data = convert_abbreviation_pdf(args.pdf)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("Kısaltma dizini: {}".format(args.output))
        return 0
    service = AnalysisService(Settings())
    if args.command == "abbreviations" and args.abbreviation_command == "status":
        print(
            json.dumps(
                service.abbreviations.metadata,
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
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
