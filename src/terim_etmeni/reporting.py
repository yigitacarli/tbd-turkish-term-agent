"""Analiz sonuçlarını JSON ve CSV biçimlerinde kaydetme."""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False


STATUS_LABELS = {
    "missing_terms": "İnceleme gerekli",
    "possible_matches": "Yakın eşleşme",
    "dictionary_matches": "Sözlükte bulundu",
    "rejected_candidates": "Elenen aday",
}

_REVIEW_DETAILS = {
    "dictionary_matches": ("Bilgi", "İşlem gerekmez", "Sözlükte doğrudan Türkçe karşılık bulundu."),
    "possible_matches": ("Orta", "Yakın eşleşmeyi doğrula", "Yazım veya tekil-çoğul farkı nedeniyle yakın sözlük eşleşmesi bulundu."),
    "missing_terms": ("Yüksek", "Terimi insan incelemesine al", "Sözlükte eşleşme bulunamadı; otomatik ekleme yapılmadı."),
    "rejected_candidates": ("Düşük", "Yok say", "Biçimsel gürültü veya düşük güvenli aday olarak elendi."),
}


def _pages(item: dict[str, object]) -> str:
    return ", ".join(str(page) for page in item.get("pages", []))


def report_rows(result: dict[str, object]) -> list[dict[str, object]]:
    """Excel'de karar vermeyi kolaylaştıran, öncelik sıralı satırlar üretir."""
    rows: list[dict[str, object]] = []
    for group in ("missing_terms", "possible_matches", "dictionary_matches", "rejected_candidates"):
        status = STATUS_LABELS[group]
        items = result.get(group, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            translations = item.get("translations", [])
            suggestions = item.get("possible_dictionary_terms", [])
            suggestion_text = " | ".join(
                "{} → {}".format(value.get("en", ""), value.get("tr", ""))
                for value in suggestions
                if isinstance(value, dict)
            ) if isinstance(suggestions, list) else ""
            priority, action, explanation = _REVIEW_DETAILS[group]
            if group == "missing_terms":
                priority = {
                    "high": "Yüksek",
                    "medium": "Orta",
                    "low": "Düşük",
                }.get(str(item.get("review_priority", "high")), "Yüksek")
                explanation = (
                    "Sözlükte eşleşme bulunamadı; kaynak, tekrar ve model "
                    "doğrulaması birlikte değerlendirilerek {} güven puanı aldı."
                ).format(item.get("review_score", "-"))
            rows.append(
                {
                    "İnceleme Durumu": status,
                    "Öncelik": priority,
                    "Önerilen İşlem": action,
                    "İngilizce Terim": item.get("term", ""),
                    "Türkçe Karşılık": ", ".join(str(value) for value in translations),
                    "Yakın Sözlük Eşleşmesi": suggestion_text,
                    "Kanıt Sayfaları": _pages(item),
                    "PDF'deki Geçiş Sayısı": item.get("occurrence_count", 0),
                    "Açıklama": explanation,
                }
            )
    return rows


def format_terminal_report(result: dict[str, object]) -> str:
    """Terminale kısa, karar odaklı bir özet yazar; ayrıntılar CSV'dedir."""
    lines = ["", "=== TERİM RAPORU ===", "CSV'de önce yüksek öncelikli inceleme adayları yer alır."]
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
        if group == "rejected_candidates":
            lines.append("  - Ayrıntılar CSV raporunda.")
            continue
        for item in values[:10]:
            if not isinstance(item, dict):
                continue
            detail = ""
            if group == "dictionary_matches":
                translations = item.get("translations", [])
                if translations:
                    detail = " -> " + " | ".join(str(value) for value in translations)
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
        if len(values) > 10:
            lines.append("  - … {} aday daha; ayrıntılar CSV raporunda.".format(len(values) - 10))
    return "\n".join(lines)


def _export_styled_xlsx(
    result: dict[str, object],
    rows: list[dict[str, object]],
    fieldnames: list[str],
    xlsx_path: Path,
) -> None:
    if not _HAS_OPENPYXL:
        return

    from openpyxl.styles import Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Terim Raporu"
    ws.views.sheetView[0].showGridLines = True

    counts = result.get("counts", {})
    if not isinstance(counts, dict):
        counts = {}

    doc_name = Path(str(result.get("document", "Dokuman"))).name
    model_name = str(result.get("model") or "Belirtilmedi")

    # Title Banner (Row 1-2)
    ws.merge_cells("A1:I1")
    title_cell = ws["A1"]
    title_cell.value = f"📊 TBD TERİM ANALİZ RAPORU — {doc_name}"
    title_cell.font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
    title_cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 25

    ws.merge_cells("A2:I2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Kullanılan Model: {model_name} | Toplam Terim Adayı: {len(rows)} | Kaynak: TBD Bilişim Sözlüğü"
    sub_cell.font = Font(name="Calibri", size=10, italic=True, color="595959")
    sub_cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[2].height = 18

    # KPI Summary Cards (Row 4-5)
    cards = [
        ("SÖZLÜKTE BULUNDU", counts.get("dictionary_matches", 0), "E2EFDA", "375623", "A4:B4", "A5:B5"),
        ("YAKIN EŞLEŞME", counts.get("possible_matches", 0), "FFF2CC", "7F6000", "C4:D4", "C5:D5"),
        ("İNCELENMESİ GEREKLİ", counts.get("missing_terms", 0), "FCE4D6", "C65911", "E4:F4", "E5:F5"),
        ("ELENEN ADAY", counts.get("rejected_candidates", 0), "F2F2F2", "595959", "G4:H4", "G5:H5"),
    ]

    for label, val, bg_color, fg_color, m1, m2 in cards:
        ws.merge_cells(m1)
        ws.merge_cells(m2)
        top_c = ws[m1.split(":")[0]]
        val_c = ws[m2.split(":")[0]]

        top_c.value = label
        top_c.font = Font(name="Calibri", size=9, bold=True, color=fg_color)
        top_c.fill = PatternFill(start_color=bg_color, fill_type="solid")
        top_c.alignment = Alignment(horizontal="center", vertical="center")

        val_c.value = val
        val_c.font = Font(name="Calibri", size=16, bold=True, color=fg_color)
        val_c.fill = PatternFill(start_color=bg_color, fill_type="solid")
        val_c.alignment = Alignment(horizontal="center", vertical="center")

    ws.row_dimensions[4].height = 18
    ws.row_dimensions[5].height = 24

    # Header Row (Row 7)
    header_row = 7
    ws.row_dimensions[header_row].height = 26
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_idx, h_text in enumerate(fieldnames, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=h_text)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    status_styles = {
        "Sözlükte bulundu": (PatternFill(start_color="E2EFDA", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="274E13")),
        "Yakın eşleşme": (PatternFill(start_color="FFF2CC", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="B25900")),
        "İnceleme gerekli": (PatternFill(start_color="FCE4D6", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="C65911")),
        "Elenen aday": (PatternFill(start_color="EDEDED", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="595959")),
    }

    priority_styles = {
        "Yüksek": (PatternFill(start_color="FADBD8", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="78281F")),
        "Orta": (PatternFill(start_color="FCF3CF", fill_type="solid"), Font(name="Calibri", size=10, bold=True, color="7D6608")),
        "Düşük": (PatternFill(start_color="E8F8F5", fill_type="solid"), Font(name="Calibri", size=10, color="117864")),
        "Bilgi": (PatternFill(start_color="EBF5FB", fill_type="solid"), Font(name="Calibri", size=10, color="1B4F72")),
    }

    thin_border = Border(
        left=Side(style="thin", color="E0E0E0"),
        right=Side(style="thin", color="E0E0E0"),
        top=Side(style="thin", color="E0E0E0"),
        bottom=Side(style="thin", color="E0E0E0"),
    )
    alt_fill = PatternFill(start_color="F9FAFB", fill_type="solid")

    for row_idx, r_dict in enumerate(rows, start=header_row + 1):
        ws.row_dimensions[row_idx].height = 20
        is_even = (row_idx % 2 == 0)

        for col_idx, key in enumerate(fieldnames, 1):
            val = r_dict.get(key, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = thin_border
            cell.font = Font(name="Calibri", size=10)
            cell.alignment = Alignment(vertical="center")

            if is_even:
                cell.fill = alt_fill

            if key == "İnceleme Durumu" and val in status_styles:
                fill, font = status_styles[val]
                cell.fill = fill
                cell.font = font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif key == "Öncelik" and val in priority_styles:
                fill, font = priority_styles[val]
                cell.fill = fill
                cell.font = font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif key == "İngilizce Terim":
                cell.font = Font(name="Calibri", size=10, bold=True, color="1F4E79")
            elif key == "Türkçe Karşılık":
                cell.font = Font(name="Calibri", size=10, color="1D6F42")
            elif key in ("Kanıt Sayfaları", "PDF'deki Geçiş Sayısı"):
                cell.alignment = Alignment(horizontal="center", vertical="center")

    ws.freeze_panes = f"A{header_row + 1}"
    last_row = header_row + len(rows)
    ws.auto_filter.ref = f"A{header_row}:I{max(last_row, header_row + 1)}"

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            if cell.row < header_row:
                continue
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 52)

    wb.save(xlsx_path)


def _model_directory_name(model: object) -> str:
    """Ollama etiketini Windows ve macOS'ta güvenli bir klasör adına çevirir."""
    value = unicodedata.normalize("NFKC", str(model or "bilinmeyen-model")).strip()
    value = re.sub(r"[\\/:*?\"<>|\s]+", "-", value)
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-_")
    return value.casefold() or "bilinmeyen-model"


def write_reports(result: dict[str, object], output_dir: Path) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    stem = Path(str(result["document"])).stem
    doc_dir = output_dir / _model_directory_name(result.get("model")) / stem
    doc_dir.mkdir(parents=True, exist_ok=True)
    json_path = doc_dir / "{}_terms.json".format(stem)
    csv_path = doc_dir / "{}_terim_raporu.csv".format(stem)
    xlsx_path = doc_dir / "{}_terim_raporu.xlsx".format(stem)

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    rows = report_rows(result)
    fieldnames = [
        "İnceleme Durumu",
        "Öncelik",
        "Önerilen İşlem",
        "İngilizce Terim",
        "Türkçe Karşılık",
        "Yakın Sözlük Eşleşmesi",
        "Kanıt Sayfaları",
        "PDF'deki Geçiş Sayısı",
        "Açıklama",
    ]

    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    _export_styled_xlsx(result, rows, fieldnames, xlsx_path)

    return json_path, csv_path
