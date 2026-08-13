"""V2'nin sade yerel web arayüzü."""
from __future__ import annotations

import html
import ipaddress
import json
import tempfile
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import Settings
from .dictionary_update import check_and_update
from .evaluation import LABELS, build_acceptance_template, load_result_payloads
from .service import AnalysisBusyError, AnalysisService


MAX_REQUEST_BYTES = 60 * 1024 * 1024
LOOPBACK_HOST_NAMES = {"localhost"}

STYLE = """
:root{--ink:#172033;--muted:#65738a;--line:#d8e1ec;--brand:#087f73;--brand2:#07665d;--bg:#f3f6fa;--ok:#e6f7f0;--warn:#fff4d6;--bad:#fee9e9}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.5}.top{background:linear-gradient(125deg,#073b4c,#087f73);color:white;padding:28px 22px 64px}.wrap{max-width:980px;margin:auto}.top h1{font-size:30px;margin:3px 0}.top p{margin:0;color:#d8fffa}.main{margin-top:-38px;padding:0 18px 40px}.card{background:white;border:1px solid var(--line);border-radius:15px;box-shadow:0 8px 24px rgba(30,52,78,.07);padding:20px;margin-bottom:14px}.dictionary{display:flex;justify-content:space-between;gap:16px;align-items:center;background:var(--ok)}.dictionary b{font-size:16px}.dictionary small,.muted{display:block;color:var(--muted);font-size:12px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.field label{display:block;font-weight:750;font-size:13px;margin-bottom:6px}.field input,.field select{width:100%;padding:11px;border:1px solid #b8c5d6;border-radius:9px;background:white;font:inherit}.drop{grid-column:1/-1;border:2px dashed #9db2c8;border-radius:12px;padding:17px;background:#f8fbfd}.button{display:inline-block;border:0;border-radius:9px;padding:11px 17px;background:var(--brand);color:white;font-weight:800;text-decoration:none;cursor:pointer;margin-top:15px}.button:hover{background:var(--brand2)}.secondary{background:white;color:var(--brand);border:1px solid var(--brand);margin-top:0}.notice{padding:11px 13px;border-radius:9px;margin-bottom:14px}.notice.ok{background:var(--ok)}.notice.failed{background:var(--bad)}.notice.current{background:var(--warn)}.results{display:grid;grid-template-columns:1fr 280px;gap:14px}.term{border-top:1px solid var(--line);padding:10px 2px}.term:first-child{border:0}.term b{display:block}.term small{color:var(--muted)}.metric{padding:11px;border-radius:10px;background:#f7f9fc;margin-bottom:8px}.metric strong{font-size:22px;display:block}.actions{display:grid;gap:8px}.actions a{text-align:center}.danger{background:var(--bad);padding:12px;border-radius:9px}.nav{display:flex;gap:10px;flex-wrap:wrap}.nav a{color:white}.management details{border-top:1px solid var(--line);margin-top:16px;padding-top:12px}.review-row{border-top:1px solid var(--line);padding:14px 0}.review-row:first-child{border-top:0}.review-row b{display:block}.review-options{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}.review-options label{border:1px solid var(--line);border-radius:8px;padding:7px 10px;background:#f8fafc;cursor:pointer;font-size:13px}.footer{text-align:center;color:var(--muted);font-size:12px;margin-top:20px}@media(max-width:720px){.grid,.results{grid-template-columns:1fr}.dictionary{display:block}.dictionary .button{margin-top:12px}.top h1{font-size:26px}.review-options{display:grid}}
"""


def _document(
    content: str, *, management: bool = False, subtitle: str = ""
) -> str:
    if not subtitle:
        subtitle = (
            "Sözlük yönetimi"
            if management
            else "Güncel sözlükle makaledeki eksik teknik terimleri bulun"
        )
    nav = '<div class="nav"><a href="/">Makale analizi</a><a href="/evaluation">İç değerlendirme</a><a href="/dictionary">Sözlük yönetimi</a></div>'
    return """<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Türkçe Terim Etmeni V2</title><style>{}</style></head><body><header class="top"><div class="wrap"><small>V2</small><h1>Türkçe Terim Etmeni</h1><p>{}</p>{}</div></header><main class="wrap main">{}<div class="footer">Son karar insan incelemesiyle verilir; sözlük otomatik değiştirilmez.</div></main></body></html>""".format(STYLE, html.escape(subtitle), nav, content)


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
    abbreviation_matches = [
        item for item in possible if item.get("match_source") == "tbd_abbreviations"
    ]
    dictionary_possible = [
        item for item in possible if item.get("match_source") != "tbd_abbreviations"
    ]
    found = [item for item in result.get("dictionary_matches", []) if isinstance(item, dict)]

    def items(values: list[dict[str, object]]) -> str:
        if not values:
            return '<p class="muted">Bu grupta terim yok.</p>'
        rendered = []
        for item in values:
            source = ""
            if item.get("match_source") == "tbd_abbreviations":
                suggestions = item.get("possible_dictionary_terms", [])
                expansions = " | ".join(
                    "{} → {}".format(value.get("en", ""), value.get("tr", ""))
                    for value in suggestions
                    if isinstance(value, dict)
                ) if isinstance(suggestions, list) else ""
                source = "<small>Kısaltma kaynağı: {}</small>".format(
                    html.escape(expansions)
                )
            rendered.append(
                '<div class="term"><b>{}</b>{}<small>Sayfa: {} · Geçiş: {}</small></div>'.format(
                html.escape(str(item.get("term", ""))),
                source,
                html.escape(", ".join(str(page) for page in item.get("pages", []))),
                html.escape(str(item.get("occurrence_count", 0))),
            )
            )
        return "".join(rendered)

    status = str(result.get("analysis_status", "complete"))
    warning = ""
    if status != "complete":
        warning = '<div class="danger"><b>Analiz {}.</b> Bu sonuç “0 eksik terim” olarak yorumlanmamalıdır.</div>'.format(
            "kısmi tamamlandı" if status == "partial" else "tamamlanamadı"
        )
    left = '<section class="card"><h2>Öncelikli sözlük açıkları</h2>{}<h3>Kısaltma kaynağında</h3>{}<h3>Yakın sözlük eşleşmeleri</h3>{}<details><summary>Diğer sonuçlar</summary><p>{} terim ana sözlükte bulundu; {} ikincil aday var.</p></details></section>'.format(
        items(primary), items(abbreviation_matches), items(dictionary_possible), len(found), len(missing) - len(primary)
    )
    right = '<aside class="card"><div class="metric"><strong>{}</strong>Öncelikli açık</div><div class="metric"><strong>{}</strong>Yakın eşleşme</div><div class="metric"><strong>{}</strong>Sözlükte bulunan</div><p class="muted">Sözlük sürümü: {}<br>Model: {}</p><div class="actions"><a class="button" href="/reports/{}">Excel raporu</a><a class="button secondary" href="/reports/{}">CSV raporu</a><a class="button secondary" href="/reports/{}">Teknik JSON</a><a class="button secondary" href="/">Yeni makale</a></div></aside>'.format(
        len(primary), len(possible), len(found), html.escape(str(result.get("dictionary_version", ""))), html.escape(str(result.get("model", ""))), urllib.parse.quote(links["xlsx"]), urllib.parse.quote(links["csv"]), urllib.parse.quote(links["json"])
    )
    return _document(warning + '<div class="results">{}{}</div>'.format(left, right))


def dictionary_html(service: AnalysisService, message: str = "", message_type: str = "ok") -> str:
    status = service.dictionary_status()
    abbreviation_status = service.abbreviations.metadata
    notice = '<div class="notice {}">{}</div>'.format(message_type, html.escape(message)) if message else ""
    content = """{}<section class="card management"><h2>Etkin sözlük</h2><p><b>Sürüm:</b> {}<br><b>Kayıt:</b> {:,}<br><b>Benzersiz İngilizce terim:</b> {:,}<br><b>Kaynak:</b> {}</p><p class="muted">Yeni kaynak tamamen doğrulanmadan bu sözlük değişmez.</p><h2>Ayrı kısaltma kaynağı</h2><p><b>Sürüm:</b> {}<br><b>Okunan kayıt:</b> {:,}<br><b>Benzersiz kısaltma:</b> {:,}</p><p class="muted">Ana sözlüğe birleştirilmez; eşleşmeler raporda kaynak etiketiyle gösterilir.</p><h2>Güncellemeyi kontrol et</h2><form action="/dictionary/check" method="post"><button class="button" type="submit">TBD sitesini kontrol et</button></form><details open><summary><b>Sözlük PDF'sini elle yükle</b></summary><p class="muted">Site otomatik erişime izin vermezse resmî İngilizce–Türkçe PDF burada doğrulanabilir.</p><form action="/dictionary/import" method="post" enctype="multipart/form-data"><div class="field"><input type="file" name="dictionary" accept="application/pdf,.pdf" required></div><button class="button" type="submit">Doğrula ve etkinleştir</button></form></details></section>""".format(
        notice, html.escape(status.version), status.record_count, status.unique_count, html.escape(status.source), html.escape(str(abbreviation_status.get("version", ""))), int(abbreviation_status.get("raw_record_count", 0)), int(abbreviation_status.get("unique_abbreviation_count", 0))
    )
    return _document(content, management=True)


def evaluation_html(message: str = "") -> str:
    notice = (
        '<div class="notice failed">{}</div>'.format(html.escape(message))
        if message
        else ""
    )
    content = """{}<section class="card"><h2>İç değerlendirme kümesi</h2><p>Analiz raporlarındaki bütün adayları tek karar listesinde birleştirin.</p><div class="notice current"><b>Bu çalışma uzman onayı değildir.</b> İlk kalite ölçümünü birlikte oluşturmak için iç değerlendirme olarak kaydedilir.</div><form action="/evaluation/prepare" method="post" enctype="multipart/form-data"><div class="grid"><div class="field drop"><label>V1 JSON raporları (isteğe bağlı)</label><input type="file" name="v1_reports" accept="application/json,.json" multiple></div><div class="field drop"><label>V2 JSON raporları (isteğe bağlı)</label><input type="file" name="v2_reports" accept="application/json,.json" multiple></div></div><p class="muted">En az bir rapor seçin. Birden fazla makaleyi aynı anda yükleyebilirsiniz.</p><button class="button" type="submit">Karar listesini hazırla</button></form></section>""".format(
        notice
    )
    return _document(content, subtitle="Gerçek makaleler için iç kalite değerlendirmesi")


def evaluation_label_html(template: dict[str, object]) -> str:
    documents = template.get("documents", [])
    if not isinstance(documents, list) or not documents:
        raise ValueError("Raporlarda etiketlenecek belge bulunamadı.")
    sections: list[str] = []
    candidate_index = 0
    for document in documents:
        if not isinstance(document, dict):
            continue
        document_name = str(document.get("document", "")).strip()
        terms = document.get("terms", [])
        if not isinstance(terms, list) or not terms:
            continue
        rows: list[str] = []
        for item in terms:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term", "")).strip()
            observed = item.get("observed_in", [])
            observed_values = observed if isinstance(observed, list) else []
            observed_json = json.dumps(observed_values, ensure_ascii=False)
            evidence = item.get("evidence", [])
            evidence_values = evidence if isinstance(evidence, list) else []
            evidence_json = json.dumps(evidence_values, ensure_ascii=False)
            page_values = sorted(
                {
                    int(page)
                    for entry in evidence_values
                    if isinstance(entry, dict)
                    for page in entry.get("pages", [])
                    if isinstance(page, int) or str(page).isdigit()
                }
            )
            rows.append(
                """<div class="review-row"><b>{term}</b><small class="muted">Kanıt sayfaları: {pages}</small><details><summary class="muted">Sistem grubunu göster</summary><small>{observed}</small></details><input type="hidden" name="document_{index}" value="{document}"><input type="hidden" name="term_{index}" value="{term_value}"><input type="hidden" name="observed_{index}" value="{observed_value}"><input type="hidden" name="evidence_{index}" value="{evidence_value}"><div class="review-options"><label><input type="radio" name="label_{index}" value="dictionary_match" required> Sözlükte var</label><label><input type="radio" name="label_{index}" value="missing_term" required> Gerçek sözlük açığı</label><label><input type="radio" name="label_{index}" value="noise" required> Gürültü</label></div></div>""".format(
                    term=html.escape(term),
                    pages=html.escape(", ".join(str(page) for page in page_values) or "-"),
                    observed=html.escape(", ".join(str(value) for value in observed_values)),
                    index=candidate_index,
                    document=html.escape(document_name, quote=True),
                    term_value=html.escape(term, quote=True),
                    observed_value=html.escape(observed_json, quote=True),
                    evidence_value=html.escape(evidence_json, quote=True),
                )
            )
            candidate_index += 1
        if rows:
            sections.append(
                '<section class="card"><h2>{}</h2><p class="muted">{} aday</p>{}</section>'.format(
                    html.escape(document_name), len(rows), "".join(rows)
                )
            )
    if candidate_index == 0:
        raise ValueError("Raporlarda etiketlenecek terim adayı bulunamadı.")
    form = """<div class="notice current"><b>İç değerlendirme:</b> Her aday için bir karar verin. Eksik karar varsa dosya oluşturulmaz.</div><form action="/evaluation/export" method="post"><input type="hidden" name="candidate_count" value="{}">{}<section class="card"><button class="button" type="submit">Kabul kümesini JSON olarak indir</button><a class="button secondary" href="/evaluation">Raporları yeniden seç</a></section></form>""".format(
        candidate_index, "".join(sections)
    )
    return _document(form, subtitle="İç değerlendirme karar listesi")


def acceptance_from_fields(fields: dict[str, str]) -> dict[str, object]:
    try:
        candidate_count = int(fields.get("candidate_count", "0"))
    except ValueError as error:
        raise ValueError("Aday sayısı geçersiz.") from error
    if candidate_count <= 0 or candidate_count > 10_000:
        raise ValueError("Aday sayısı geçersiz.")
    documents: dict[str, dict[str, object]] = {}
    for index in range(candidate_count):
        document = fields.get("document_{}".format(index), "").strip()
        term = fields.get("term_{}".format(index), "").strip()
        label = fields.get("label_{}".format(index), "").strip()
        if not document or not term:
            raise ValueError("Belge veya terim bilgisi eksik.")
        if label not in LABELS:
            raise ValueError("Bütün adaylar için bir karar verin.")
        observed_raw = fields.get("observed_{}".format(index), "[]")
        try:
            observed = json.loads(observed_raw)
        except json.JSONDecodeError as error:
            raise ValueError("Aday kaynak bilgisi geçersiz.") from error
        if not isinstance(observed, list):
            raise ValueError("Aday kaynak bilgisi geçersiz.")
        evidence_raw = fields.get("evidence_{}".format(index), "[]")
        try:
            evidence = json.loads(evidence_raw)
        except json.JSONDecodeError as error:
            raise ValueError("Aday kanıt bilgisi geçersiz.") from error
        if not isinstance(evidence, list):
            raise ValueError("Aday kanıt bilgisi geçersiz.")
        key = Path(document).name.casefold()
        target = documents.setdefault(
            key, {"document": Path(document).name, "terms": []}
        )
        terms = target["terms"]
        if isinstance(terms, list):
            terms.append(
                {
                    "term": term,
                    "label": label,
                    "observed_in": observed,
                    "evidence": evidence,
                }
            )
    return {
        "schema_version": 1,
        "review_status": "internal_review",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "documents": list(documents.values()),
    }


def _multipart(
    handler: BaseHTTPRequestHandler,
) -> tuple[dict[str, str], dict[str, list[tuple[str, bytes]]]]:
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
    files: dict[str, list[tuple[str, bytes]]] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        if part.get_filename():
            files.setdefault(name, []).append(
                (part.get_filename() or "dosya", payload)
            )
        else:
            fields[name] = payload.decode(part.get_content_charset() or "utf-8")
    return fields, files


def _urlencoded(handler: BaseHTTPRequestHandler) -> dict[str, str]:
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as error:
        raise ValueError("Geçersiz istek boyutu.") from error
    if length <= 0 or length > MAX_REQUEST_BYTES:
        raise ValueError("Form boyutu geçersiz veya çok büyük.")
    content_type = handler.headers.get("Content-Type", "")
    if not content_type.startswith("application/x-www-form-urlencoded"):
        raise ValueError("Form verisi okunamadı.")
    try:
        raw = handler.rfile.read(length).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Form verisi okunamadı.") from error
    values = urllib.parse.parse_qs(raw, keep_blank_values=True, strict_parsing=True)
    return {key: value[-1] for key, value in values.items() if value}


class V2Server(ThreadingHTTPServer):
    def __init__(self, address, service: AnalysisService) -> None:
        self.service = service
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: V2Server

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/healthz":
            self._health(); return
        if path == "/":
            self._html(index_html(self.server.service)); return
        if path == "/evaluation":
            self._html(evaluation_html()); return
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
                filename, payload = files["pdf"][0]
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
            if path == "/evaluation/prepare":
                _, files = _multipart(self)
                systems: dict[str, dict[str, dict[str, object]]] = {}
                for system_name, field_name in (
                    ("v1", "v1_reports"),
                    ("v2", "v2_reports"),
                ):
                    uploads = files.get(field_name, [])
                    if uploads:
                        systems[system_name] = load_result_payloads(uploads)
                if not systems:
                    raise ValueError("En az bir JSON raporu seçin.")
                template = build_acceptance_template(systems)
                self._html(evaluation_label_html(template)); return
            if path == "/evaluation/export":
                acceptance = acceptance_from_fields(_urlencoded(self))
                self._json_download(
                    acceptance,
                    "internal_acceptance_set.json",
                ); return
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
                _, payload = files["dictionary"][0]
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as target:
                    target.write(payload); temporary = Path(target.name)
                try:
                    status = self.server.service.dictionaries.import_pdf(temporary)
                finally:
                    temporary.unlink(missing_ok=True)
                self._html(dictionary_html(self.server.service, "{} sürümlü sözlük etkin.".format(status.version), "ok")); return
            self.send_error(404)
        except AnalysisBusyError as error:
            self._html(index_html(self.server.service, str(error), "current"), 503)
        except Exception as error:
            if path.startswith("/dictionary"):
                self._html(dictionary_html(self.server.service, str(error), "failed"), 400)
            elif path.startswith("/evaluation"):
                self._html(evaluation_html(str(error)), 400)
            else:
                self._html(index_html(self.server.service, str(error), "failed"), 400)

    def _report(self, encoded: str) -> None:
        root = self.server.service.settings.output_dir.resolve()
        candidate = (root / Path(urllib.parse.unquote(encoded))).resolve()
        if root not in candidate.parents or not candidate.is_file() or candidate.suffix not in {".json", ".csv", ".xlsx"}:
            self.send_error(404); return
        payload = candidate.read_bytes()
        content_type = {".json":"application/json; charset=utf-8", ".csv":"text/csv; charset=utf-8", ".xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}[candidate.suffix]
        self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(candidate.name)); self._security_headers(); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

    def _html(self, content: str, status: int = 200) -> None:
        payload = content.encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self._security_headers(); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)

    def _health(self) -> None:
        payload = b'{"status":"ok"}\n'
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'unsafe-inline'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'",
        )

    def _json_download(self, content: dict[str, object], filename: str) -> None:
        payload = (json.dumps(content, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        )
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header(
            "Content-Disposition", 'attachment; filename="{}"'.format(filename)
        )
        self._security_headers()
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def validate_bind_host(host: str) -> str:
    normalized = host.strip().strip("[]")
    if normalized.casefold() in LOOPBACK_HOST_NAMES:
        return normalized
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError as error:
        raise ValueError(
            "HTTPS ve kimlik doğrulama eklenmeden yalnız localhost kullanılabilir."
        ) from error
    if not address.is_loopback:
        raise ValueError(
            "HTTPS ve kimlik doğrulama eklenmeden yalnız localhost kullanılabilir."
        )
    return normalized


def serve(
    host: str = "127.0.0.1", port: int = 8876, *, open_browser: bool = True
) -> None:
    host = validate_bind_host(host)
    service = AnalysisService(Settings())
    server = V2Server((host, port), service)
    url_host = "[{}]".format(host) if ":" in host else host
    url = "http://{}:{}".format(url_host, port)
    print("Türkçe Terim Etmeni V2: {}".format(url), flush=True)
    print("Durdurmak için Control-C.", flush=True)
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nV2 kapatıldı.")
    finally:
        server.server_close()
