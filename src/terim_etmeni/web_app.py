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
:root{--ink:#172033;--muted:#61708a;--line:#dbe3ee;--brand:#087f73;--brand2:#0f766e;--bg:#f4f7fb;--white:#fff;--found:#e7f8f2;--possible:#fff6d9;--missing:#feecec;--rejected:#edf1f7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.5}
.top{background:linear-gradient(125deg,#073b4c,#087f73);color:#fff;padding:34px 24px 70px}.top-inner,.main{max-width:1040px;margin:auto}.eyebrow{font-size:12px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;opacity:.8}.top h1{font-size:34px;line-height:1.15;margin:8px 0}.top p{max-width:680px;margin:0;color:#d9fffa}
.main{margin-top:-42px;padding:0 20px 50px}.card{background:#fff;border:1px solid var(--line);border-radius:16px;box-shadow:0 10px 30px rgba(30,52,78,.08);padding:24px;margin-bottom:20px}
.status{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 15px;border-radius:10px;background:#f6f9fc;margin-bottom:20px}.dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:8px}.ok{background:#12a779}.bad{background:#dc4c64}.status small{color:var(--muted)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.field label{display:block;font-size:13px;font-weight:750;margin-bottom:7px}.field input,.field select{width:100%;padding:12px;border:1px solid #b9c6d8;border-radius:9px;background:#fff;color:var(--ink);font:inherit}.field input:focus,.field select:focus{outline:3px solid #bcece6;border-color:var(--brand)}
.drop{grid-column:1/-1;border:2px dashed #9fb3c8;border-radius:12px;padding:22px;background:#f8fbfd}.drop input{border:0;padding:4px;background:transparent}.hint{font-size:12px;color:var(--muted);margin-top:6px}.button{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:10px;background:var(--brand);color:#fff;font-weight:800;font-size:15px;padding:13px 20px;cursor:pointer;margin-top:20px;min-width:190px}.button:hover{background:var(--brand2)}.button:disabled{opacity:.6;cursor:wait}.error{background:#fff0f1;color:#9e2638;border:1px solid #ffc8cf;border-radius:10px;padding:14px;margin-bottom:18px}
.loading{display:none;margin-left:14px;color:var(--muted);font-size:13px}.loading.show{display:inline}.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.metric{padding:15px;border-radius:12px;border:1px solid var(--line)}.metric b{font-size:24px;display:block}.metric span{font-size:12px;color:var(--muted)}
.section{border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-top:14px}.section h3{margin:0;padding:13px 16px;font-size:15px}.found h3{background:var(--found)}.possible h3{background:var(--possible)}.missing h3{background:var(--missing)}.rejected h3{background:var(--rejected)}
.terms{list-style:none;margin:0;padding:0}.terms li{padding:12px 16px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:18px}.term-main{font-weight:700}.term-detail{color:var(--muted);font-size:13px}.evidence{white-space:nowrap;color:var(--muted);font-size:12px}.empty{padding:12px 16px;color:var(--muted)}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}.link-button{display:inline-block;text-decoration:none;border:1px solid var(--brand);color:var(--brand);padding:10px 14px;border-radius:9px;font-weight:750}.link-button:hover{background:#e9faf7}.footer{text-align:center;color:var(--muted);font-size:12px;margin-top:30px}
@media(max-width:700px){.grid{grid-template-columns:1fr}.summary{grid-template-columns:1fr 1fr}.terms li{display:block}.evidence{margin-top:5px}.top h1{font-size:28px}}
"""


SCRIPT = """
document.addEventListener('DOMContentLoaded',()=>{const form=document.querySelector('#scan-form');if(!form)return;form.addEventListener('submit',()=>{const button=form.querySelector('button');const loading=form.querySelector('.loading');button.disabled=true;button.textContent='Analiz ediliyor...';loading.classList.add('show')})});
"""


def _document(content: str) -> str:
    return """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TBD Dictionary Control</title><style>{}</style></head><body><header class="top"><div class="top-inner"><div class="eyebrow">Yerel PDF Analizi</div><h1>TBD Dictionary Control</h1><p>İngilizce teknik terimleri çıkarır, İngilizce-Türkçe sözlükle karşılaştırır ve eksik terimleri kanıtlarıyla raporlar.</p></div></header><main class="main">{}<div class="footer">Veriler bu bilgisayarda işlenir. Sunucu yalnızca 127.0.0.1 adresinde çalışır.</div></main><script>{}</script></body></html>""".format(STYLE, content, SCRIPT)


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
        detail = "Sözlükte eşleşme bulunamadı"
    else:
        detail = "Düşük güvenli aday"
    pages = ", ".join(str(value) for value in item.get("pages", []))
    evidence = "Sayfa {} · {} geçiş".format(
        html.escape(pages or "-"), html.escape(str(item.get("occurrence_count", 0)))
    )
    return '<li><div><div class="term-main">{}</div><div class="term-detail">{}</div></div><div class="evidence">{}</div></li>'.format(
        term, detail, evidence
    )


def result_html(result: dict[str, object], json_name: str, csv_name: str) -> str:
    counts = result.get("counts", {})
    groups = [
        ("dictionary_matches", "found", "Sözlükte bulunanlar"),
        ("possible_matches", "possible", "Olası eşleşmeler"),
        ("missing_terms", "missing", "Sözlükte olmayanlar"),
        ("rejected_candidates", "rejected", "Elenen düşük güvenli adaylar"),
    ]
    sections = []
    for key, css_class, title in groups:
        items = result.get(key, [])
        values = items if isinstance(items, list) else []
        body = "".join(_item_html(item, key) for item in values if isinstance(item, dict))
        if not body:
            body = '<div class="empty">Bu grupta terim yok.</div>'
        sections.append(
            '<section class="section {}"><h3>{} ({})</h3><ul class="terms">{}</ul></section>'.format(
                css_class, title, len(values), body
            )
        )
    metrics = [
        ("dictionary_matches", "Bulunan"),
        ("possible_matches", "Olası"),
        ("missing_terms", "Eksik"),
        ("rejected_candidates", "Elenen"),
    ]
    metric_html = "".join(
        '<div class="metric"><b>{}</b><span>{}</span></div>'.format(
            counts.get(key, 0) if isinstance(counts, dict) else 0, label
        )
        for key, label in metrics
    )
    return '<div class="card"><h2>{}</h2><p class="term-detail">Model: {} · Sözlük: {} · {} sayfa</p><div class="summary">{}</div>{}<div class="actions"><a class="link-button" href="/reports/{}">CSV raporunu indir</a><a class="link-button" href="/reports/{}">JSON raporunu indir</a><a class="link-button" href="/">Yeni PDF tara</a></div></div>'.format(
        html.escape(str(result.get("document", "Analiz sonucu"))),
        html.escape(str(result.get("model", ""))),
        html.escape(str(result.get("dictionary_version", ""))),
        html.escape(str(result.get("page_count", ""))),
        metric_html,
        "".join(sections),
        urllib.parse.quote(csv_name),
        urllib.parse.quote(json_name),
    )


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
        selected = self.settings.model
        options = "".join(
            '<option value="{}"{}>{}</option>'.format(
                html.escape(name, quote=True),
                " selected" if name == selected else "",
                html.escape(name),
            )
            for name in models
        )
        if selected not in models:
            options = '<option value="{}" selected>{}</option>'.format(
                html.escape(selected, quote=True), html.escape(selected)
            ) + options
        if connection_error:
            status = '<div><span class="dot bad"></span><b>Ollama bağlantısı yok</b><br><small>{}</small></div>'.format(
                html.escape(connection_error)
            )
        else:
            status = '<div><span class="dot ok"></span><b>Ollama hazır</b><br><small>{} model bulundu</small></div>'.format(
                len(models)
            )
        error_box = '<div class="error"><b>Analiz tamamlanamadı:</b> {}</div>'.format(
            html.escape(error_message)
        ) if error_message else ""
        content = '{}<div class="card"><div class="status">{}<small>Sözlük: {:,} terim</small></div><form id="scan-form" action="/analyze" method="post" enctype="multipart/form-data"><div class="grid"><div class="field drop"><label>Analiz edilecek PDF</label><input type="file" name="pdf" accept="application/pdf,.pdf" required><div class="hint">En fazla 50 MB, metin katmanlı PDF. Taranmış belgeler için önce OCR gerekir.</div></div><div class="field"><label>Yerel model</label><select name="model" required>{}</select><div class="hint">Ollama uygulamasında yüklü modeller listelenir.</div></div><div class="field"><label>Çalışma biçimi</label><input value="Yerel Ollama · veriler bilgisayardan çıkmaz" disabled></div></div><button class="button" type="submit">PDF’yi analiz et</button><span class="loading">Büyük belgeler birkaç dakika sürebilir.</span></form></div>'.format(
            error_box, status, len(self.dictionary), options
        )
        return _document(content)

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
            model = fields.get("model", self.server.application.settings.model).strip()
            if not model:
                raise ValueError("Bir model seçin.")
            result, json_path, csv_path = self.server.application.analyze(
                filename, content, model
            )
            self._html(result_html(result, json_path.name, csv_path.name))
        except Exception as error:
            self._html(self.server.application.index_html(str(error)), status=400)

    def _report(self, encoded_name: str) -> None:
        name = Path(urllib.parse.unquote(encoded_name)).name
        output_dir = self.server.application.settings.output_dir.resolve()
        path = (output_dir / name).resolve()
        if path.parent != output_dir or not path.is_file() or path.suffix not in {".csv", ".json"}:
            self.send_error(404)
            return
        content = path.read_bytes()
        content_type = "text/csv; charset=utf-8" if path.suffix == ".csv" else "application/json; charset=utf-8"
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
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    application = WebApplication()
    server = ApplicationServer((host, port), application)
    url = "http://{}:{}".format(host, port)
    print("TBD Dictionary Control arayüzü: {}".format(url), flush=True)
    print("Durdurmak için Control-C tuşlarına basın.", flush=True)
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArayüz kapatıldı.")
    finally:
        server.server_close()
