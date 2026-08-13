"""V2 komut satırı."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .abbreviation_pdf import convert_abbreviation_pdf
from .config import Settings
from .dictionary_update import check_and_update
from .evaluation import (
    EvaluationError,
    build_acceptance_template,
    compare_systems,
    format_comparison,
    load_acceptance_set,
    load_result_reports,
)
from .service import AnalysisService
from .replay import ReplayError, load_candidate_snapshot, replay_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="turkce-terim-etmeni-v2")
    sub = parser.add_subparsers(dest="command", required=True)
    serve_parser = sub.add_parser("serve", help="V2 web arayüzünü başlat")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8876)
    serve_parser.add_argument(
        "--no-browser", action="store_true", help="Tarayıcıyı otomatik açma"
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
    evaluate = sub.add_parser(
        "evaluate", help="Etiketli kabul kümesinde V1 ve V2 raporlarını karşılaştır"
    )
    evaluate.add_argument("acceptance_set", type=Path)
    evaluate.add_argument(
        "--v1-result", type=Path, action="append", required=True, dest="v1_results"
    )
    evaluate.add_argument(
        "--v2-result", type=Path, action="append", required=True, dest="v2_results"
    )
    evaluate.add_argument("--output", type=Path, help="Ölçüm özetini JSON olarak yaz")
    prepare = sub.add_parser(
        "prepare-acceptance",
        help="V1/V2 raporlarının aday birleşiminden etiketleme şablonu üret",
    )
    prepare.add_argument(
        "--v1-result", type=Path, action="append", default=[], dest="v1_results"
    )
    prepare.add_argument(
        "--v2-result", type=Path, action="append", default=[], dest="v2_results"
    )
    prepare.add_argument("--output", type=Path, required=True)
    replay = sub.add_parser(
        "replay", help="Sabit aday anlık görüntüsünü Ollama çağırmadan yeniden sınıflandır"
    )
    replay.add_argument("candidate_snapshot", type=Path)
    replay.add_argument("--output", type=Path, required=True)
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
    if args.command == "evaluate":
        try:
            acceptance = load_acceptance_set(args.acceptance_set)
            result = compare_systems(
                acceptance,
                {
                    "v1": load_result_reports(args.v1_results),
                    "v2": load_result_reports(args.v2_results),
                },
            )
        except EvaluationError as error:
            parser.error(str(error))
        print(format_comparison(result))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print("JSON ölçüm özeti: {}".format(args.output))
        return 0
    if args.command == "prepare-acceptance":
        try:
            systems = {}
            if args.v1_results:
                systems["v1"] = load_result_reports(args.v1_results)
            if args.v2_results:
                systems["v2"] = load_result_reports(args.v2_results)
            if not systems:
                raise EvaluationError("En az bir V1 veya V2 sonuç raporu gerekir.")
            template = build_acceptance_template(systems)
        except EvaluationError as error:
            parser.error(str(error))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(template, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("Etiketleme şablonu: {}".format(args.output))
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
    if args.command == "replay":
        try:
            snapshot = load_candidate_snapshot(args.candidate_snapshot)
            result = replay_snapshot(
                snapshot,
                service.dictionaries.load_index(),
                service.abbreviations,
            )
        except ReplayError as error:
            parser.error(str(error))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("Çevrimdışı replay raporu: {}".format(args.output))
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
