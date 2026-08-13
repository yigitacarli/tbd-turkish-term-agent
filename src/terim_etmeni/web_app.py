"""Kurulum gerektirmeyen yerel tarayıcı arayüzü."""
from __future__ import annotations

import html
import json
import tempfile
import threading
import urllib.parse
import webbrowser
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .config import Settings
from .dictionary import DictionaryIndex
from .ollama_client import OllamaClient, OllamaError
from .pipeline import analyze_pdf
from .reporting import write_reports


MAX_UPLOAD_BYTES = 50 * 1024 * 1024


STYLE = """
:root{--ink:#172033;--muted:#61708a;--line:#dbe3ee;--brand:#087f73;--brand2:#0f766e;--bg:#f4f7fb;--white:#fff;--found:#e7f8f2;--possible:#fff6d9;--missing:#feecec;--rejected:#edf1f7;--acronym:#f0f4ff;--low:#fff1e6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.5}
.top{background:linear-gradient(125deg,#073b4c,#087f73);color:#fff;padding:25px 24px 58px}.top-inner,.main{max-width:1120px;margin:auto}.eyebrow{font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;opacity:.8}.top h1{font-size:30px;line-height:1.15;margin:5px 0}
.main{margin-top:-34px;padding:0 20px 38px}.card{background:#fff;border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 22px rgba(30,52,78,.07);padding:20px;margin-bottom:14px}
.status{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 13px;border-radius:10px;background:#f6f9fc;margin-bottom:16px}.dot{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:8px}.ok{background:#12a779}.bad{background:#dc4c64}.status small{color:var(--muted)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.field label{display:block;font-size:13px;font-weight:750;margin-bottom:6px}.field input,.field select{width:100%;padding:10px 11px;border:1px solid #b9c6d8;border-radius:9px;background:#fff;color:var(--ink);font:inherit}.field input:focus,.field select:focus{outline:3px solid #bcece6;border-color:var(--brand)}
.drop{grid-column:1/-1;border:2px dashed #9fb3c8;border-radius:12px;padding:17px;background:#f8fbfd}.drop input{border:0;padding:4px;background:transparent}.hint{font-size:12px;color:var(--muted);margin-top:5px}.button{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:9px;background:var(--brand);color:#fff;font-weight:800;font-size:14px;padding:11px 17px;cursor:pointer;margin-top:16px;min-width:180px}.button:hover{background:var(--brand2)}.button:disabled{opacity:.6;cursor:wait}.error{background:#fff0f1;color:#9e2638;border:1px solid #ffc8cf;border-radius:10px;padding:12px;margin-bottom:14px}
.loading{display:none;margin-left:12px;color:var(--muted);font-size:12px}.loading.show{display:inline}.summary{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:12px 0}.metric{padding:10px 11px;border-radius:10px;border:1px solid var(--line);background:#fbfcfe}.metric b{font-size:21px;display:block;line-height:1.1}.metric span{font-size:11px;color:var(--muted)}.metric-dictionary_matches{background:var(--found)}.metric-possible_matches{background:var(--possible)}.metric-missing_terms{background:var(--missing)}.metric-rejected_candidates{background:var(--rejected)}
.section{border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-top:10px}.section h3{margin:0;padding:10px 13px;font-size:14px}.found h3{background:var(--found)}.possible h3{background:var(--possible)}.missing h3{background:var(--missing)}.rejected h3{background:var(--rejected)}
.terms{list-style:none;margin:0;padding:0}.terms li{padding:9px 13px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:14px}.term-main{font-weight:700;font-size:14px}.term-detail{color:var(--muted);font-size:12px}.evidence{white-space:nowrap;color:var(--muted);font-size:11px}.empty{padding:10px 13px;color:var(--muted);font-size:13px}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}.link-button{display:inline-block;text-decoration:none;border:1px solid var(--brand);color:var(--brand);padding:9px 12px;border-radius:8px;font-weight:750;font-size:13px}.link-button:hover{background:#e9faf7}.footer{text-align:center;color:var(--muted);font-size:12px;margin-top:22px}
.model-picker{grid-column:1/-1}.warnings{font-size:12px;color:#8b5d10;margin:8px 0}.intro{margin:0 0 16px;color:var(--muted);font-size:14px}.model-settings{margin-top:12px;border:1px solid var(--line);border-radius:10px;background:#fbfcfe}.model-settings summary{cursor:pointer;padding:10px 12px;font-size:13px;font-weight:750}.model-settings .field{padding:0 12px 12px}
.setup{padding:18px}.setup>summary{cursor:pointer;font-weight:800;font-size:14px}.setup-content{padding-top:14px}.setup h2{margin:0 0 10px;font-size:18px}.setup-grid,.model-grid{display:grid;gap:12px}.setup-grid{grid-template-columns:repeat(2,1fr)}.model-grid{grid-template-columns:repeat(3,1fr);margin-bottom:12px}.setup-step,.model-card{border:1px solid var(--line);border-radius:10px;padding:12px;background:#fbfcfe}.setup-step b,.model-card b{display:block;margin-bottom:5px}.model-card p{margin:0;color:var(--muted);font-size:13px}.model-card.recommended{border-color:#72bdb2;background:#f2fbf9}.setup-step ol{margin:6px 0 0;padding-left:20px;font-size:13px}.setup-step li{margin:5px 0}.setup code{font-size:12px;overflow-wrap:anywhere}@media(max-width:700px){.setup-grid,.model-grid{grid-template-columns:1fr}}
.result-head{background:linear-gradient(120deg,#073b4c,#087f73);color:#fff;border-radius:14px;padding:20px 22px;margin-bottom:14px;box-shadow:0 8px 22px rgba(7,59,76,.16)}.result-head h2{margin:4px 0;font-size:24px;overflow-wrap:anywhere}.result-meta{margin:0;color:#d9fffa;font-size:12px}.review-layout{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(245px,.45fr);gap:14px}.review-panel{padding:17px}.review-panel h2{margin:0 0 3px;font-size:18px}.review-panel>p{margin:0 0 10px;color:var(--muted);font-size:12px}.review-section{margin-top:9px;border:1px solid var(--line);border-radius:10px}.review-section h3{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);border-radius:9px 9px 0 0;padding:9px 11px;margin:0;font-size:13px}.review-section.possible h3{background:var(--possible);border-bottom-color:#f2d994}.review-section.missing h3{background:var(--missing);border-bottom-color:#f3c3c3}.review-section.found h3{background:var(--found);border-bottom-color:#c8eedf}.review-section.rejected h3{background:var(--rejected);border-bottom-color:#d4dfea}.review-section.acronym h3{background:var(--acronym);border-bottom-color:#d0dcfa}.review-section.low h3{background:var(--low);border-bottom-color:#f1cdb6}.count-pill{font-size:11px;background:#fff;padding:1px 7px;border-radius:99px;border:1px solid rgba(0,0,0,.08)}.details{margin-top:12px;border:1px solid var(--line);border-radius:10px;background:#fff}.details summary{cursor:pointer;padding:11px 13px;font-weight:750;color:var(--ink);font-size:13px}.details .section{margin:0;border:0;border-top:1px solid var(--line);border-radius:0}.result-actions{display:grid;gap:7px;margin-top:12px}.result-actions .link-button{text-align:center}.quality-note{border-left:4px solid var(--brand);background:#f2fbf9;padding:10px 11px;border-radius:0 9px 9px 0;font-size:12px;margin-top:12px}
@media(max-width:700px){.grid,.review-layout{grid-template-columns:1fr}.summary{grid-template-columns:1fr 1fr}.terms li{display:block}.evidence{margin-top:5px}.top h1{font-size:28px}.result-head h2{font-size:23px}}
"""


SCRIPT = """
document.addEventListener('DOMContentLoaded',()=>{const form=document.querySelector('#scan-form');if(form)form.addEventListener('submit',()=>{const button=form.querySelector('button');const loading=form.querySelector('.loading');button.disabled=true;button.textContent='Analiz ediliyor...';loading.classList.add('show')});});
"""


def _document(content: str) -> str:
    return """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Türkçe Terim Etmeni</title><style>{}</style></head><body><header class="top"><div class="top-inner"><div class="eyebrow">Yerel PDF Analizi</div><h1>Türkçe Terim Etmeni</h1></div></header><main class="main">{}</main><script>{}</script></body></html>""".format(STYLE, content, SCRIPT)


def _item_html(item: dict[str, object], group: str) -> str:
    term = html.escape(str(item.get("term", "")))
    detail = ""
    if group == "dictionary_matches":
        detail = "Türkçe: " + " | ".join(
            html.escape(str(value)) for value in item.get("translations", [])
        )
    elif group == "possible_matches":
        matches = item.get("possible_dictionary_terms", [])
        detail = "Olası: " + " | ".join(
            "{} → {}".format(
                html.escape(str(value.get("en", ""))),
                html.escape(str(value.get("tr", ""))),
            )
            for value in matches
            if isinstance(value, dict)
        )
    elif group == "missing_terms":
        priority = {"high": "Yüksek güven", "medium": "Kontrol edilmeli"}.get(
            str(item.get("review_priority", "high")), "Kontrol edilmeli"
        )
        detail = "{} · sözlükte eşleşme bulunamadı".format(priority)
    else:
        detail = "Düşük güvenli aday"
    pages = ", ".join(str(value) for value in item.get("pages", []))
    evidence = "Sayfa {} · {} geçiş".format(
        html.escape(pages or "-"), html.escape(str(item.get("occurrence_count", 0)))
    )
    return '<li><div><div class="term-main">{}</div><div class="term-detail">{}</div></div><div class="evidence">{}</div></li>'.format(
        term, detail, evidence
    )


def result_html(result: dict[str, object], json_name: str, csv_name: str, xlsx_name: str = "") -> str:
    if not xlsx_name:
        xlsx_name = csv_name.replace("_terim_raporu.csv", "_terim_raporu.xlsx")
    raw_missing = result.get("missing_terms", [])
    raw_missing = raw_missing if isinstance(raw_missing, list) else []
    missing = [
        item for item in raw_missing
        if isinstance(item, dict) and item.get("review_priority") != "low"
    ]
    # Eski raporlar açıldığında düşük güvenli adayları ana karar listesine sokma.
    legacy_low = [
        item for item in raw_missing
        if isinstance(item, dict) and item.get("review_priority") == "low"
    ]
    possible_values = result.get("possible_matches", [])
    possible = [item for item in possible_values if isinstance(item, dict)] if isinstance(possible_values, list) else []
    found_values = result.get("dictionary_matches", [])
    found = [item for item in found_values if isinstance(item, dict)] if isinstance(found_values, list) else []
    rejected_values = result.get("rejected_candidates", [])
    rejected = [item for item in rejected_values if isinstance(item, dict)] if isinstance(rejected_values, list) else []
    rejected.extend(legacy_low)

    def section(key: str, css_class: str, title: str, values: list[dict[str, object]]) -> str:
        body = "".join(_item_html(item, key) for item in values)
        if not body:
            body = '<div class="empty">Bu grupta terim yok.</div>'
        return '<div class="review-section {}"><h3>{} <span class="count-pill">{}</span></h3><ul class="terms">{}</ul></div>'.format(
            css_class, title, len(values), body
        )

    missing_section = section("missing_terms", "missing", "İncelenecek sözlük açıkları", missing)
    possible_section = section("possible_matches", "possible", "Yakın sözlük eşleşmeleri", possible)
    found_section = section("dictionary_matches", "found", "Sözlükte bulunan terimler", found)
    rejected_section = section("rejected_candidates", "rejected", "Elenen düşük güvenli adaylar", rejected)
    metric_values = [
        ("missing_terms", len(missing), "İncelenecek"),
        ("possible_matches", len(possible), "Yakın eşleşme"),
        ("dictionary_matches", len(found), "Sözlükte bulunan"),
        ("rejected_candidates", len(rejected), "Elenen"),
    ]
    metric_html = "".join(
        '<div class="metric metric-{}"><b>{}</b><span>{}</span></div>'.format(key, value, label)
        for key, value, label in metric_values
    )
    warnings = result.get("processing_warnings", [])
    status = result.get("analysis_status", "complete")
    failed_chunks = result.get("failed_chunk_count", 0)
    if status == "failed":
        warning_html = (
            '<div class="error"><b>Model analizi tamamlanamadı.</b> '
            'Hiçbir metin parçasından model yanıtı alınamadı. Aşağıdaki sayılar '
            'yalnız deterministik sözlük taramasıdır; “0 eksik” anlamına gelmez. '
            'Modeli veya Ollama bağlantısını denetleyip belgeyi yeniden tarayın.</div>'
        )
    elif status == "partial":
        review = result.get("technical_review", {})
        review_failed = isinstance(review, dict) and review.get("status") == "failed"
        if failed_chunks:
            message = (
                "{} metin parçası model yanıtı olmadan atlandı; "
                "eksik terim listesi tam olmayabilir."
            ).format(html.escape(str(failed_chunks)))
        elif review_failed:
            message = (
                "İkinci model doğrulaması tamamlanamadı; sonuçlar kaynak, tekrar "
                "ve ilk model sinyaliyle puanlandı."
            )
        else:
            message = "Analizin bir bölümü tamamlanamadı; sonuçları dikkatle inceleyin."
        warning_html = '<div class="warnings"><b>Eksik analiz:</b> {}</div>'.format(message)
    elif warnings:
        warning_html = '<div class="warnings">Model doğrulama uyarısı: {}</div>'.format(
            html.escape(" | ".join(str(value) for value in warnings))
        )
    else:
        warning_html = ""
    status_label = "Analiz tamamlandı" if status == "complete" else "Analiz eksik kaldı"
    return '<section class="result-head"><div class="eyebrow">{}</div><h2>{}</h2><p class="result-meta">{} sayfa · Model: {} · Sözlük sürümü: {}</p></section>{}<div class="review-layout"><section class="card review-panel"><h2>Karar listesi</h2><p>Önce aşağıdaki sözlük açıklarını doğrulayın. Bilgi ve denetim listeleri kapalı tutulur.</p>{}{}<details class="details"><summary>Sözlükte bulunanlar ({})</summary>{}</details><details class="details"><summary>Elenen adaylar ({})</summary>{}</details></section><aside class="card review-panel"><h2>Rapor özeti</h2><div class="summary">{}</div><div class="quality-note">Eksik sayısı yalnız puan eşiğini geçen inceleme adaylarını gösterir.</div><div class="result-actions"><a class="link-button primary" href="/reports/{}">Excel Raporunu indir</a><a class="link-button" href="/reports/{}">İnceleme CSV’sini indir</a><a class="link-button" href="/reports/{}">Teknik JSON’u indir</a><a class="link-button" href="/">Yeni PDF tara</a></div></aside></div>'.format(
        status_label,
        html.escape(str(result.get("document", "Analiz sonucu"))),
        html.escape(str(result.get("page_count", ""))),
        html.escape(str(result.get("model", ""))),
        html.escape(str(result.get("dictionary_version", ""))),
        warning_html,
        missing_section,
        possible_section,
        len(found),
        found_section,
        len(rejected),
        rejected_section,
        metric_html,
        urllib.parse.quote(xlsx_name),
        urllib.parse.quote(csv_name),
        urllib.parse.quote(json_name),
    )


def _preferred_installed_model(models: list[str], configured: str) -> str:
    """Yalnız açık OLLAMA_MODEL ayarı kuruluysa ön seçim yapar."""
    return configured if configured in models else ""


def _model_label(name: str, selected: bool = False) -> str:
    suffix = " · ortam ayarı" if selected else ""
    return "{}{}".format(name, suffix)


def _setup_html() -> str:
    """Model seçimi ve her bilgisayarda görünen kısa kurulum yönergesi."""
    return """<details class="card setup"><summary>Kurulum ve model rehberi</summary><div class="setup-content"><h2>Model seçimi</h2>
<p class="intro">Uygulama belirli bir modele bağlı değildir. Ollama'da kurulu modeller otomatik listelenir; her analizde kullanacağınız modeli siz seçersiniz.</p>
<div class="model-grid"><div class="model-card"><b>Küçük modeller</b><p>Daha hızlı ve düşük bellek kullanımı</p></div>
<div class="model-card"><b>Orta modeller</b><p>Hız ve terim bulma dengesi</p></div>
<div class="model-card"><b>Büyük modeller</b><p>Daha güçlü donanım ve daha uzun analiz</p></div></div>
<h2>Kurulum</h2>
<div class="setup-grid"><div class="setup-step"><b>macOS</b><ol>
<li><a href="https://ollama.com/download" target="_blank" rel="noreferrer">Ollama'yı indirip kurun</a>.</li>
<li>Terminal'i açın ve seçtiğiniz güncel model için <code>ollama pull MODEL_ETIKETI</code> komutunu çalıştırın.</li>
<li>Bu sayfayı yenileyin.</li></ol></div>
<div class="setup-step"><b>Windows</b><ol>
<li><a href="https://ollama.com/download" target="_blank" rel="noreferrer">Ollama'yı indirip kurun</a>.</li>
<li>PowerShell'i açın ve seçtiğiniz güncel model için <code>ollama pull MODEL_ETIKETI</code> komutunu çalıştırın.</li>
<li>Bu sayfayı yenileyin.</li></ol></div></div></div></details>"""


class WebApplication:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        self.dictionary = DictionaryIndex.load(self.settings.dictionary_path)

    def model_status(self) -> tuple[list[str], Optional[str]]:
        try:
            client = OllamaClient(self.settings.ollama_url, self.settings.model, timeout=2)
            return client.installed_models(), None
        except OllamaError as error:
            return [], str(error)

    def index_html(self, error_message: str = "") -> str:
        models, connection_error = self.model_status()
        selected = ""
        if connection_error:
            status = '<div><span class="dot bad"></span><b>Ollama bağlantısı yok</b><br><small>{}</small></div>'.format(
                html.escape(connection_error)
            )
            options = '<option value="">Ollama kurulmadı veya çalışmıyor</option>'
            model_disabled = " disabled"
            submit_disabled = " disabled"
        else:
            status = '<div><span class="dot ok"></span><b>Ollama hazır</b><br><small>{} model bulundu</small></div>'.format(
                len(models)
            )
            selected = _preferred_installed_model(models, self.settings.model)
            placeholder = (
                '<option value="" disabled{}>Bir model seçin</option>'.format(
                    "" if selected else " selected"
                )
            )
            options = placeholder + "".join(
                '<option value="{}"{}>{}</option>'.format(
                    html.escape(name, quote=True),
                    " selected" if name == selected else "",
                    html.escape(_model_label(name, name == selected)),
                )
                for name in models
            )
            if not models:
                options = '<option value="">Kurulu Ollama modeli bulunamadı</option>'
                model_disabled = " disabled"
                submit_disabled = " disabled"
            else:
                model_disabled = ""
                submit_disabled = ""
        error_box = '<div class="error"><b>Analiz tamamlanamadı:</b> {}</div>'.format(
            html.escape(error_message)
        ) if error_message else ""
        selected_label = _model_label(selected, True) if selected else "Model seçin"
        content = '{}<div class="card"><div class="status">{}<small>Sözlük: {:,} terim</small></div><p class="intro">PDF’yi seçin; uygulama yalnız sözlükte bulunmayan, incelenmeye değer terimleri öne çıkarsın.</p><form id="scan-form" action="/analyze" method="post" enctype="multipart/form-data"><div class="grid"><div class="field drop"><label>İngilizce makaleyi seçin</label><input type="file" name="pdf" accept="application/pdf,.pdf" required></div></div><details class="model-settings"><summary>{}</summary><div class="field model-picker"><label>Ollama modeli</label><select id="model-select" name="model" required{}>{}</select></div></details><button class="button" type="submit"{}>Eksik terimleri bul</button><span class="loading">Analiz sürüyor...</span></form></div>{}'.format(
            error_box, status, len(self.dictionary), html.escape(selected_label),
            model_disabled, options, submit_disabled, _setup_html()
        )
        return _document(content)

    def latest_result_html(self) -> str | None:
        """Son kaydedilen raporu, sonuç ekranını doğrudan açan kullanıcılar için sunar."""
        reports = sorted(
            self.settings.output_dir.glob("**/*_terms.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for json_path in reports:
            try:
                result = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(result, dict):
                continue
            stem = json_path.name.removesuffix("_terms.json")
            # Değerlendirme çalışmaları model/belge gibi birden fazla alt
            # klasörde tutulabilir. Yalnız son klasör adını kullanmak sonuç
            # ekranını açsa bile indirme bağlantılarını 404'e düşürüyordu.
            report_dir = json_path.parent.relative_to(self.settings.output_dir)
            json_rel = str(report_dir / json_path.name)
            csv_rel = str(report_dir / f"{stem}_terim_raporu.csv")
            xlsx_rel = str(report_dir / f"{stem}_terim_raporu.xlsx")
            return _document(result_html(result, json_rel, csv_rel, xlsx_rel))
        return None

    def analyze(self, filename: str, pdf_bytes: bytes, model: str) -> tuple[dict[str, object], Path, Path]:
        safe_name = Path(filename or "belge.pdf").name
        if not safe_name.casefold().endswith(".pdf") or not pdf_bytes.startswith(b"%PDF-"):
            raise ValueError("Geçerli bir PDF dosyası seçin.")
        if len(pdf_bytes) > MAX_UPLOAD_BYTES:
            raise ValueError("PDF 50 MB sınırını aşıyor.")
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as file:
                file.write(pdf_bytes)
                temporary = Path(file.name)
            client = OllamaClient(
                self.settings.ollama_url, model, timeout=self.settings.timeout_seconds
            )
            client.check_model()
            result = analyze_pdf(
                temporary,
                self.dictionary,
                client,
                model,
                self.settings.chunk_size,
                self.settings.chunk_overlap,
            )
            result["document"] = safe_name
            json_path, csv_path = write_reports(result, self.settings.output_dir)
            return result, json_path, csv_path
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def _multipart(handler: BaseHTTPRequestHandler) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as error:
        raise ValueError("Geçersiz istek boyutu.") from error
    if length <= 0 or length > MAX_UPLOAD_BYTES + 1024 * 1024:
        raise ValueError("Yükleme boyutu geçersiz veya çok büyük.")
    content_type = handler.headers.get("Content-Type", "")
    raw = handler.rfile.read(length)
    message = BytesParser(policy=default).parsebytes(
        ("Content-Type: {}\r\nMIME-Version: 1.0\r\n\r\n".format(content_type)).encode()
        + raw
    )
    if not message.is_multipart():
        raise ValueError("Form verisi okunamadı.")
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename:
            files[name] = (filename, payload)
        else:
            fields[name] = payload.decode(part.get_content_charset() or "utf-8")
    return fields, files


class ApplicationServer(ThreadingHTTPServer):
    def __init__(self, address, application: WebApplication) -> None:
        self.application = application
        super().__init__(address, RequestHandler)


class RequestHandler(BaseHTTPRequestHandler):
    server: ApplicationServer

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            self._html(self.server.application.index_html())
            return
        if path == "/analyze":
            latest = self.server.application.latest_result_html()
            if latest:
                self._html(latest)
            else:
                self._html(self.server.application.index_html("Henüz bir rapor yok. Lütfen PDF seçip analizi başlatın."))
            return
        if path.startswith("/reports/"):
            self._report(path[len("/reports/") :])
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urllib.parse.urlparse(self.path).path != "/analyze":
            self.send_error(404)
            return
        try:
            fields, files = _multipart(self)
            if "pdf" not in files:
                raise ValueError("Bir PDF dosyası seçin.")
            filename, content = files["pdf"]
            model = fields.get("model", "").strip()
            if not model:
                raise ValueError("Bir model seçin.")
            result, json_path, csv_path = self.server.application.analyze(
                filename, content, model
            )
            report_dir = json_path.parent.relative_to(
                self.server.application.settings.output_dir
            )
            stem = json_path.name.removesuffix("_terms.json")
            json_rel = str(report_dir / json_path.name)
            csv_rel = str(report_dir / csv_path.name)
            xlsx_rel = str(report_dir / f"{stem}_terim_raporu.xlsx")
            self._html(_document(result_html(result, json_rel, csv_rel, xlsx_rel)))
        except Exception as error:
            self._html(self.server.application.index_html(str(error)), status=400)

    def _report(self, encoded_name: str) -> None:
        rel_path = Path(urllib.parse.unquote(encoded_name))
        output_dir = self.server.application.settings.output_dir.resolve()
        path = (output_dir / rel_path).resolve()
        try:
            if not path.is_relative_to(output_dir) or not path.is_file() or path.suffix not in {".csv", ".json", ".xlsx"}:
                self.send_error(404)
                return
        except (ValueError, AttributeError):
            if output_dir not in path.parents or not path.is_file() or path.suffix not in {".csv", ".json", ".xlsx"}:
                self.send_error(404)
                return
        content = path.read_bytes()
        if path.suffix == ".csv":
            content_type = "text/csv; charset=utf-8"
        elif path.suffix == ".xlsx":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            content_type = "application/json; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(path.name))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _html(self, content: str, status: int = 200) -> None:
        payload = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    application = WebApplication()
    server = ApplicationServer((host, port), application)
    url = "http://{}:{}".format(host, port)
    print("Türkçe Terim Etmeni arayüzü: {}".format(url), flush=True)
    print("Durdurmak için Control-C tuşlarına basın.", flush=True)
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArayüz kapatıldı.")
    finally:
        server.server_close()
