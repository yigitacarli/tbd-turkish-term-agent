"""V2'nin sade yerel web arayüzü."""
from __future__ import annotations

import html
import json
import tempfile
import urllib.parse
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import Settings
from .dictionary_update import check_and_update
from .service import AnalysisService


MAX_REQUEST_BYTES = 60 * 1024 * 1024

STYLE = """
:root{--ink:#172033;--muted:#65738a;--line:#d8e1ec;--brand:#087f73;--brand2:#07665d;--bg:#f3f6fa;--ok:#e6f7f0;--warn:#fff4d6;--bad:#fee9e9}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.5}.top{background:linear-gradient(125deg,#073b4c,#087f73);color:white;padding:28px 22px 64px}.wrap{max-width:980px;margin:auto}.top h1{font-size:30px;margin:3px 0}.top p{margin:0;color:#d8fffa}.main{margin-top:-38px;padding:0 18px 40px}.card{background:white;border:1px solid var(--line);border-radius:15px;box-shadow:0 8px 24px rgba(30,52,78,.07);padding:20px;margin-bottom:14px}.dictionary{display:flex;justify-content:space-between;gap:16px;align-items:center;background:var(--ok)}.dictionary b{font-size:16px}.dictionary small,.muted{display:block;color:var(--muted);font-size:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.field label{display:block;font-weight:750;font-size:13px;margin-bottom:6px}.field input,.field select{width:100%;padding:11px;border:1px solid #b8c5d6;border-radius:9px;background:white;font:inherit}.drop{grid-column:1/-1;border:2px dashed #9db2c8;border-radius:12px;padding:17px;background:#f8fbfd}.button{display:inline-block;border:0;border-radius:9px;padding:11px 17px;background:var(--brand);color:white;font-weight:800;text-decoration:none;cursor:pointer;margin-top:15px}.button:hover{background:var(--brand2)}.secondary{background:white;color:var(--brand);border:1px solid var(--brand);margin-top:0}.notice{padding:11px 13px;border-radius:9px;margin-bottom:14px}.notice.ok{background:var(--ok)}.notice.failed{background:var(--bad)}.notice.current{background:var(--warn)}.results{display:grid;grid-template-columns:1fr 280px;gap:14px}.term{border-top:1px solid var(--line);padding:10px 2px}.term:first-child{border:0}.term b{display:block}.term small{color:var(--muted)}.metric{padding:11px;border-radius:10px;background:#f7f9fc;margin-bottom:8px}.metric strong{font-size:22px;display:block}.actions{display:grid;gap:8px}.actions a{text-align:center}.danger{background:var(--bad);padding:12px;border-radius:9px}.nav{display:flex;gap:10px;flex-wrap:wrap}.nav a{color:white}.management details{border-top:1px solid var(--line);margin-top:16px;padding-top:12px}.footer{text-align:center;color:var(--muted);font-size:12px;margin-top:20px}@media(max-width:720px){.grid,.results{grid-template-columns:1fr}.dictionary{display:block}.dictionary .button{margin-top:12px}.top h1{font-size:26px}}
"""


def _document(content: str, *, management: bool = False) -> str:
    subtitle = "Sözlük yönetimi" if management else "Güncel sözlükle makaledeki eksik teknik terimleri bulun"
    nav = '<div class="nav"><a href="/">Makale analizi</a><a href="/dictionary">Sözlük yönetimi</a></div>'
    return """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Türkçe Terim Etmeni V2</title><style>{}</style></head><body><header class="top"><div class="wrap"><small>V2</small><h1>Türkçe Terim Etmeni</h1><p>{}</p>{}</div></header><main class="wrap main">{}<div class="footer">Kararlar uzman incelemesine sunulur; sözlük otomatik değiştirilmez.</div></main></body></html>""".format(STYLE, subtitle, nav, content)


def _status_card(service: AnalysisService) -> str:
    status = service.dictionary_status()
    return '<section class="card dictionary"><div><b>Güncel sözlük: {}</b><small>{:,} kayıt · {:,} benzersiz İngilizce terim</small></div><a class="button secondary" href="/dictionary">Sözlüğü yönet</a></section>'.format(
        html.escape(status.version), status.record_count, status.unique_count
    )


def index_html(service: AnalysisService, message: str = "", message_type: str = "failed") -> str:
    models, model_error = service.installed_models()
    configured = service.settings.model if service.settings.model in models else ""
    selected = configured or (models[0] if len(models) == 1 else "")
    options = '<option value="" disabled{}>Bir model seçin</option>'.format("" if selected else " selected")
    options += "".join(
        '<option value="{}"{}>{}</option>'.format(
            html.escape(model, quote=True), " selected" if model == selected else "", html.escape(model)
        )
        for model in models
    )
    disabled = "" if models else " disabled"
    if not models:
        options = '<option value="">Ollama modeli bulunamadı</option>'
    notice = '<div class="notice {}">{}</div>'.format(message_type, html.escape(message)) if message else ""
    if model_error:
        notice += '<div class="danger"><b>Analiz motoruna bağlanılamadı.</b><br><span class="muted">{}</span></div>'.format(html.escape(model_error))
    form = """<section class="card"><h2>Makale analizi</h2><p class="muted">Metin katmanı bulunan İngilizce PDF'yi seçin. Sonuçta önce sözlükte bulunmayan güçlü adaylar gösterilir.</p><form action="/analyze" method="post" enctype="multipart/form-data"><div class="grid"><div class="field drop"><label>Makale PDF'si</label><input type="file" name="pdf" accept="application/pdf,.pdf" required></div><div class="field"><label>Yerel analiz modeli</label><select name="model" required{}>{}</select></div></div><button class="button" type="submit"{}>Eksik terimleri bul</button></form></section>""".format(disabled, options, disabled)
    return _document(notice + _status_card(service) + form)


def result_html(result: dict[str, object], links: dict[str, str]) -> str:
    missing = [item for item in result.get("missing_terms", []) if isinstance(item, dict)]
    primary = [item for item in missing if item.get("review_priority") != "medium"]
    possible = [item for item in result.get("possible_matches", []) if isinstance(item, dict)]
    found = [item for item in result.get("dictionary_matches", []) if isinstance(item, dict)]

    def items(values: list[dict[str, object]]) -> str:
        if not values:
            return '<p class="muted">Bu grupta terim yok.</p>'
        return "".join(
            '<div class="term"><b>{}</b><small>Sayfa: {} · Geçiş: {}</small></div>'.format(
                html.escape(str(item.get("term", ""))),
                html.escape(", ".join(str(page) for page in item.get("pages", []))),
                html.escape(str(item.get("occurrence_count", 0))),
            )
            for item in values
        )

    status = str(result.get("analysis_status", "complete"))
    warning = ""
    if status != "complete":
        warning = '<div class="danger"><b>Analiz {}.</b> Bu sonuç “0 eksik terim” olarak yorumlanmamalıdır.</div>'.format(
            "kısmi tamamlandı" if status == "partial" else "tamamlanamadı"
        )
    left = '<section class="card"><h2>Öncelikli sözlük açıkları</h2>{}<h3>Yakın eşleşmeler</h3>{}<details><summary>Diğer sonuçlar</summary><p>{} terim sözlükte bulundu; {} ikincil aday var.</p></details></section>'.format(
        items(primary), items(possible), len(found), len(missing) - len(primary)
    )
    right = '<aside class="card"><div class="metric"><strong>{}</strong>Öncelikli açık</div><div class="metric"><strong>{}</strong>Yakın eşleşme</div><div class="metric"><strong>{}</strong>Sözlükte bulunan</div><p class="muted">Sözlük sürümü: {}<br>Model: {}</p><div class="actions"><a class="button" href="/reports/{}">Excel raporu</a><a class="button secondary" href="/reports/{}">CSV raporu</a><a class="button secondary" href="/reports/{}">Teknik JSON</a><a class="button secondary" href="/">Yeni makale</a></div></aside>'.format(
        len(primary), len(possible), len(found), html.escape(str(result.get("dictionary_version", ""))), html.escape(str(result.get("model", ""))), urllib.parse.quote(links["xlsx"]), urllib.parse.quote(links["csv"]), urllib.parse.quote(links["json"])
    )
    return _document(warning + '<div class="results">{}{}</div>'.format(left, right))


def dictionary_html(service: AnalysisService, message: str = "", message_type: str = "ok") -> str:
    status = service.dictionary_status()
    notice = '<div class="notice {}">{}</div>'.format(message_type, html.escape(message)) if message else ""
    content = """{}<section class="card management"><h2>Etkin sözlük</h2><p><b>Sürüm:</b> {}<br><b>Kayıt:</b> {:,}<br><b>Benzersiz İngilizce terim:</b> {:,}<br><b>Kaynak:</b> {}</p><p class="muted">Yeni kaynak tamamen doğrulanmadan bu sözlük değişmez.</p><h2>Güncellemeyi kontrol et</h2><form action="/dictionary/check" method="post"><button class="button" type="submit">TBD sitesini kontrol et</button></form><details open><summary><b>Sözlük PDF'sini elle yükle</b></summary><p class="muted">Site otomatik erişime izin vermezse resmî İngilizce–Türkçe PDF burada doğrulanabilir.</p><form action="/dictionary/import" method="post" enctype="multipart/form-data"><div class="field"><input type="file" name="dictionary" accept="application/pdf,.pdf" required></div><button class="button" type="submit">Doğrula ve etkinleştir</button></form></details></section>""".format(
        notice, html.escape(status.version), status.record_count, status.unique_count, html.escape(status.source)
    )
    return _document(content, management=True)


def _multipart(handler: BaseHTTPRequestHandler) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as error:
        raise ValueError("Geçersiz istek boyutu.") from error
    if length <= 0 or length > MAX_REQUEST_BYTES:
        raise ValueError("Yükleme boyutu geçersiz veya çok büyük.")
    raw = handler.rfile.read(length)
    message = BytesParser(policy=default).parsebytes(
        ("Content-Type: {}\r\nMIME-Version: 1.0\r\n\r\n".format(handler.headers.get("Content-Type", ""))).encode() + raw
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
        if part.get_filename():
            files[name] = (part.get_filename() or "dosya", payload)
        else:
            fields[name] = payload.decode(part.get_content_charset() or "utf-8")
    return fields, files


class V2Server(ThreadingHTTPServer):
    def __init__(self, address, service: AnalysisService) -> None:
        self.service = service
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: V2Server

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            self._html(index_html(self.server.service)); return
        if path == "/dictionary":
            self._html(dictionary_html(self.server.service)); return
        if path.startswith("/reports/"):
            self._report(path[len("/reports/"):]); return
        self.send_error(404)

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/analyze":
                fields, files = _multipart(self)
                if "pdf" not in files:
                    raise ValueError("Makale PDF'sini seçin.")
                filename, payload = files["pdf"]
                result, json_path, csv_path, xlsx_path = self.server.service.analyze_upload(
                    filename, payload, fields.get("model", "")
                )
                base = self.server.service.settings.output_dir
                links = {
                    "json": str(json_path.relative_to(base)),
                    "csv": str(csv_path.relative_to(base)),
                    "xlsx": str(xlsx_path.relative_to(base)),
                }
                self._html(result_html(result, links)); return
            if path == "/dictionary/check":
                settings = self.server.service.settings
                result = check_and_update(
                    self.server.service.dictionaries,
                    page_url=settings.dictionary_page_url,
                    pdf_url=settings.dictionary_pdf_url,
                    timeout=settings.update_timeout_seconds,
                )
                self._html(dictionary_html(self.server.service, result.message, result.status)); return
            if path == "/dictionary/import":
                _, files = _multipart(self)
                if "dictionary" not in files:
                    raise ValueError("Sözlük PDF'sini seçin.")
                _, payload = files["dictionary"]
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as target:
                    target.write(payload); temporary = Path(target.name)
                try:
                    status = self.server.service.dictionaries.import_pdf(temporary)
                finally:
                    temporary.unlink(missing_ok=True)
                self._html(dictionary_html(self.server.service, "{} sürümlü sözlük etkin.".format(status.version), "ok")); return
            self.send_error(404)
        except Exception as error:
            if path.startswith("/dictionary"):
                self._html(dictionary_html(self.server.service, str(error), "failed"), 400)
            else:
                self._html(index_html(self.server.service, str(error), "failed"), 400)

    def _report(self, encoded: str) -> None:
        root = self.server.service.settings.output_dir.resolve()
        candidate = (root / Path(urllib.parse.unquote(encoded))).resolve()
        if root not in candidate.parents or not candidate.is_file() or candidate.suffix not in {".json", ".csv", ".xlsx"}:
            self.send_error(404); return
        payload = candidate.read_bytes()
        content_type = {".json":"application/json; charset=utf-8", ".csv":"text/csv; charset=utf-8", ".xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}[candidate.suffix]
        self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(candidate.name)); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

    def _html(self, content: str, status: int = 200) -> None:
        payload = content.encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8876) -> None:
    service = AnalysisService(Settings())
    server = V2Server((host, port), service)
    print("Türkçe Terim Etmeni V2: http://{}:{}".format(host, port), flush=True)
    print("Durdurmak için Control-C.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nV2 kapatıldı.")
    finally:
        server.server_close()

