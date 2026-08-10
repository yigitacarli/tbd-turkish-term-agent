"""Analiz sonuçlarını JSON ve CSV biçimlerinde kaydetme."""
from __future__ import annotations

import csv
import json
from pathlib import Path


STATUS_LABELS = {
    "dictionary_matches": "BULUNDU",
    "possible_matches": "OLASI EŞLEŞME",
    "missing_terms": "EKSİK",
    "rejected_candidates": "ELENEN ADAY",
}


def _pages(item: dict[str, object]) -> str:
    return ", ".join(str(page) for page in item.get("pages", []))


def report_rows(result: dict[str, object]) -> list[dict[str, object]]:
    """Bütün sonuç gruplarını insan tarafından okunabilir satırlara dönüştürür."""
    rows: list[dict[str, object]] = []
    for group, status in STATUS_LABELS.items():
        items = result.get(group, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            translations = item.get("translations", [])
            suggestions = item.get("possible_dictionary_terms", [])
            suggestion_text = " | ".join(
                "{} -> {}".format(value.get("en", ""), value.get("tr", ""))
                for value in suggestions
                if isinstance(value, dict)
            ) if isinstance(suggestions, list) else ""
            if group == "dictionary_matches":
                explanation = "Sözlükte tam eşleşme bulundu."
            elif group == "possible_matches":
                explanation = "Tire, boşluk veya tekil-çoğul farkıyla olası eşleşme."
            elif group == "missing_terms":
                explanation = "Sözlükte eşleşme bulunamadı."
            else:
                explanation = "Düşük güvenli genel sözcük veya özel ad; eksik listesine alınmadı."
            rows.append(
                {
                    "durum": status,
                    "pdf_terimi": item.get("term", ""),
                    "turkce_karsilik": " | ".join(str(value) for value in translations),
                    "olasi_sozluk_eslesmesi": suggestion_text,
                    "sayfalar": _pages(item),
                    "gecis_sayisi": item.get("occurrence_count", 0),
                    "aciklama": explanation,
                }
            )
    return rows


def format_terminal_report(result: dict[str, object]) -> str:
    """Sonuçları terminal için bölüm bölüm biçimlendirir."""
    lines = ["", "=== TERİM RAPORU ==="]
    titles = {
        "dictionary_matches": "SÖZLÜKTE BULUNANLAR",
        "possible_matches": "OLASI EŞLEŞMELER",
        "missing_terms": "SÖZLÜKTE OLMAYANLAR",
        "rejected_candidates": "ELENEN DÜŞÜK GÜVENLİ ADAYLAR",
    }
    for group, title in titles.items():
        items = result.get(group, [])
        values = items if isinstance(items, list) else []
        lines.extend(["", "{} ({})".format(title, len(values))])
        if not values:
            lines.append("  - Yok")
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            detail = ""
            if group == "dictionary_matches":
                detail = " -> " + " | ".join(item.get("translations", []))
            elif group == "possible_matches":
                matches = item.get("possible_dictionary_terms", [])
                detail = " ~ " + " | ".join(
                    "{} -> {}".format(value.get("en", ""), value.get("tr", ""))
                    for value in matches
                    if isinstance(value, dict)
                )
            pages = _pages(item)
            lines.append(
                "  - {}{} [sayfa: {}; geçiş: {}]".format(
                    item.get("term", ""),
                    detail,
                    pages or "-",
                    item.get("occurrence_count", 0),
                )
            )
    return "\n".join(lines)


def write_reports(result: dict[str, object], output_dir: Path) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(str(result["document"])).stem
    json_path = output_dir / "{}_terms.json".format(stem)
    csv_path = output_dir / "{}_terim_raporu.csv".format(stem)

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        fieldnames = [
            "durum",
            "pdf_terimi",
            "turkce_karsilik",
            "olasi_sozluk_eslesmesi",
            "sayfalar",
            "gecis_sayisi",
            "aciklama",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows(result))
    return json_path, csv_path
