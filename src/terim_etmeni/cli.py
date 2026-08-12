"""Türkçe Terim Etmeni komut satırı arayüzü."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Settings
from .dictionary import DictionaryFormatError, DictionaryIndex
from .ollama_client import OllamaClient, OllamaError
from .pdf_reader import PDFReadError
from .pipeline import analyze_pdf
from .reporting import format_terminal_report, write_reports


def _pdf_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if input_path.suffix.casefold() == ".pdf" else []
    if input_path.is_dir():
        return sorted(
            (path for path in input_path.rglob("*.pdf") if path.is_file()),
            key=lambda path: str(path).casefold(),
        )
    return []


def build_parser() -> argparse.ArgumentParser:
    defaults = Settings()
    parser = argparse.ArgumentParser(
        prog="tbd-dictionary-control",
        description="PDF'lerdeki İngilizce bilişim terimlerini yerel sözlükle karşılaştırır.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="Bir PDF'yi veya PDF klasörünü tara")
    scan.add_argument("input", type=Path, help="PDF dosyası veya PDF klasörü")
    scan.add_argument("--dictionary", type=Path, default=defaults.dictionary_path)
    scan.add_argument("--output-dir", type=Path, default=defaults.output_dir)
    scan.add_argument("--model", default=defaults.model)
    scan.add_argument("--ollama-url", default=defaults.ollama_url)
    scan.add_argument("--chunk-size", type=int, default=defaults.chunk_size)
    scan.add_argument("--overlap", type=int, default=defaults.chunk_overlap)
    scan.add_argument("--timeout", type=int, default=defaults.timeout_seconds)
    serve_parser = subparsers.add_parser("serve", help="Yerel tarayıcı arayüzünü başlat")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument(
        "--no-browser", action="store_true", help="Tarayıcıyı otomatik açma"
    )
    return parser


def run_scan(args: argparse.Namespace) -> int:
    files = _pdf_files(args.input)
    if not files:
        print("PDF bulunamadı: {}".format(args.input), file=sys.stderr)
        return 2

    try:
        dictionary = DictionaryIndex.load(args.dictionary)
        client = OllamaClient(args.ollama_url, args.model, timeout=args.timeout)
        client.check_model()
    except (DictionaryFormatError, OllamaError) as error:
        print("Başlatma hatası: {}".format(error), file=sys.stderr)
        return 2

    failures = 0
    print(
        "{} PDF, {} sözlük terimi, model: {}".format(
            len(files), len(dictionary), args.model
        ),
        flush=True,
    )
    for index, pdf_path in enumerate(files, start=1):
        print("[{}/{}] {}".format(index, len(files), pdf_path.name), flush=True)
        try:
            result = analyze_pdf(
                pdf_path=pdf_path,
                dictionary=dictionary,
                provider=client,
                model_name=args.model,
                chunk_size=args.chunk_size,
                chunk_overlap=args.overlap,
            )
            json_path, csv_path = write_reports(result, args.output_dir)
            counts = result["counts"]
            print(
                "  bulunan: {dictionary_matches}, olası: {possible_matches}, eksik: {missing_terms}".format(
                    **counts
                )
            )
            warnings = result.get("processing_warnings", [])
            if warnings:
                print(
                    "  uyarı: {}/{} parça model yanıtı olmadan atlandı".format(
                        len(warnings), result.get("chunk_count", 0)
                    ),
                    file=sys.stderr,
                )
            print(format_terminal_report(result))
            print("  raporlar: {}, {}".format(json_path, csv_path))
        except (PDFReadError, OllamaError, ValueError, OSError) as error:
            failures += 1
            print("  hata: {}".format(error), file=sys.stderr)
    return 1 if failures else 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        return run_scan(args)
    if args.command == "serve":
        from .web_app import serve

        serve(args.host, args.port, open_browser=not args.no_browser)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
