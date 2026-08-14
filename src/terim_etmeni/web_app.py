"""Türkiye Bilişim Derneği — Bilişim Terimleri Denetim Sistemi Web Arayüzü."""
from __future__ import annotations

import html
import ipaddress
import tempfile
import threading
import urllib.parse
import webbrowser
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .config import Settings
from .dictionary_update import check_and_update
from .service import AnalysisBusyError, AnalysisService


MAX_REQUEST_BYTES = 60 * 1024 * 1024
LOOPBACK_HOST_NAMES = {"localhost"}

STYLE = """
:root {
  --bg-app: #f1f5f9;
  --bg-surface: #ffffff;
  --border-subtle: #cbd5e1;
  --border-strong: #94a3b8;
  --text-primary: #0f172a;
  --text-secondary: #334155;
  --text-muted: #64748b;
  --tbd-navy: #1e3a5f;
  --tbd-navy-hover: #0f2942;
  --tbd-blue: #0284c7;
  --tbd-blue-light: #f0f9ff;
  --tbd-blue-border: #bae6fd;
  --success-bg: #ecfdf5;
  --success-text: #065f46;
  --success-border: #a7f3d0;
  --warning-bg: #fffbeb;
  --warning-text: #92400e;
  --warning-border: #fde68a;
  --danger-bg: #fef2f2;
  --danger-text: #991b1b;
  --danger-border: #fca5a5;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 12px;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg-app);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
  font-size: 18px;
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}

.app-header {
  background: var(--tbd-navy);
  color: #ffffff;
  border-bottom: 4px solid var(--tbd-blue);
  padding: 26px 0 30px;
}

.wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 18px;
  margin-bottom: 12px;
}

.header-title-block h1 {
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.01em;
}

.header-title-block .institution {
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #93c5fd;
  font-weight: 700;
  margin-bottom: 4px;
}

.nav-tabs {
  display: flex;
  gap: 8px;
  background: rgba(0, 0, 0, 0.25);
  padding: 6px;
  border-radius: var(--radius-md);
}

.nav-tabs a {
  color: #e2e8f0;
  text-decoration: none;
  font-size: 16px;
  font-weight: 700;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.nav-tabs a:hover {
  background: rgba(255, 255, 255, 0.18);
  color: #ffffff;
}

.nav-tabs a.active {
  background: #ffffff;
  color: var(--tbd-navy);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header-description {
  color: #e2e8f0;
  font-size: 17px;
  margin-top: 6px;
  line-height: 1.6;
}

.main-content {
  margin-top: 28px;
  padding-bottom: 70px;
}

.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
  padding: 32px 36px;
  margin-bottom: 28px;
}

.card-title {
  font-size: 24px;
  font-weight: 700;
  color: #0f2942;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 12px;
  margin-bottom: 20px;
}

.card-intro {
  font-size: 18px;
  color: var(--text-secondary);
  margin-bottom: 24px;
  line-height: 1.7;
}

.dict-status-strip {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-left: 5px solid var(--tbd-navy);
  border-radius: var(--radius-md);
  padding: 20px 28px;
  margin-bottom: 28px;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
}

.dict-status-info .dict-title {
  display: block;
  font-size: 19px;
  font-weight: 700;
  color: #0f2942;
  margin-bottom: 2px;
}

.dict-status-info .dict-counts {
  font-size: 16px;
  color: var(--text-secondary);
}

.active-engine-badge {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  background: #f8fafc;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 14px 20px;
  margin-bottom: 24px;
}

.engine-status-text {
  font-size: 16px;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 10px;
}

.engine-status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #16a34a;
}

.current-config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 26px;
}

.config-stat-card {
  background: #f8fafc;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
}

.config-stat-label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.config-stat-value {
  display: block;
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
}

.upload-zone {
  background: #ffffff;
  border: 2px dashed #94a3b8;
  border-radius: var(--radius-md);
  padding: 26px 30px;
  margin-bottom: 26px;
  transition: border-color 0.15s ease;
}

.upload-zone:hover {
  border-color: var(--tbd-navy);
}

.upload-label-title {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
}

.upload-hint {
  display: block;
  font-size: 16px;
  color: #64748b;
  margin-bottom: 16px;
}

.file-input-field {
  display: block;
  width: 100%;
  padding: 14px 18px;
  font-size: 17px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: #f8fafc;
  color: var(--text-primary);
  cursor: pointer;
}

.file-chosen-banner {
  margin-top: 14px;
  padding: 12px 18px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: var(--radius-sm);
  color: #065f46;
  font-size: 17px;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.form-group {
  margin-bottom: 22px;
}

.form-group label {
  display: block;
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.form-group select, .form-group input[type="text"], .form-group input[type="password"] {
  width: 100%;
  padding: 13px 16px;
  font-size: 17px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: #ffffff;
  color: var(--text-primary);
}

.form-group select:focus, .form-group input:focus {
  border-color: var(--tbd-navy);
  outline: 3px solid var(--tbd-blue-border);
}

.btn {
  display: inline-block;
  padding: 14px 28px;
  font-size: 16px;
  font-weight: 700;
  text-align: center;
  text-decoration: none;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-primary {
  background: var(--tbd-navy);
  color: #ffffff;
}

.btn-primary:hover {
  background: var(--tbd-navy-hover);
}

.btn-secondary {
  background: #ffffff;
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.btn-secondary:hover {
  background: #f8fafc;
  border-color: var(--text-primary);
}

.btn-sm {
  padding: 10px 20px;
  font-size: 15px;
}

.btn-lg {
  padding: 16px 40px;
  font-size: 19px;
}

.btn-block {
  display: block;
  width: 100%;
}

.notice {
  padding: 16px 22px;
  border-radius: var(--radius-sm);
  font-size: 17px;
  line-height: 1.6;
  margin-bottom: 24px;
  border: 1px solid transparent;
}

.notice-ok { background: var(--success-bg); color: var(--success-text); border-color: var(--success-border); }
.notice-warn { background: var(--warning-bg); color: var(--warning-text); border-color: var(--warning-border); }
.notice-danger { background: var(--danger-bg); color: var(--danger-text); border-color: var(--danger-border); }

/* Results Screen */
.summary-table-wrap {
  margin-bottom: 28px;
}

.summary-table {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
}

.summary-table th {
  background: #f8fafc;
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  text-align: left;
  padding: 16px 20px;
  border-bottom: 2px solid var(--border-subtle);
}

.summary-table td {
  padding: 18px 20px;
  font-size: 24px;
  font-weight: 700;
  border-bottom: 1px solid var(--border-subtle);
}

.results-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 28px;
  align-items: start;
}

.filter-bar {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  align-items: center;
  background: #ffffff;
  padding: 18px 22px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 24px;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
}

.filter-input {
  flex: 1;
  min-width: 240px;
  padding: 12px 18px;
  font-size: 17px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
}

.filter-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 10px 18px;
  font-size: 16px;
  font-weight: 700;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-strong);
  background: #ffffff;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-btn.active, .filter-btn:hover {
  background: var(--tbd-navy);
  color: #ffffff;
  border-color: var(--tbd-navy);
}

.term-entry {
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-left: 6px solid var(--border-strong);
  border-radius: var(--radius-sm);
  padding: 22px 26px;
  margin-bottom: 18px;
  box-shadow: 0 2px 5px rgba(15, 23, 42, 0.03);
}

.term-entry[data-group="missing"] { border-left-color: #dc2626; }
.term-entry[data-group="abbrev"] { border-left-color: #d97706; }
.term-entry[data-group="found"] { border-left-color: #16a34a; }

.term-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.term-heading {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.badge {
  font-size: 15px;
  font-weight: 700;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
}

.badge-missing { background: #fee2e2; color: #991b1b; border-color: #fca5a5; }
.badge-abbrev { background: #fef3c7; color: #92400e; border-color: #fde68a; }
.badge-found { background: #dcfce7; color: #166534; border-color: #86efac; }

.term-context-box {
  font-size: 17px;
  line-height: 1.75;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  margin: 12px 0;
  font-style: normal;
}

.term-meta-info {
  font-size: 15px;
  color: #64748b;
  display: flex;
  gap: 20px;
  font-weight: 600;
}

.export-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.footer {
  text-align: center;
  color: var(--text-muted);
  font-size: 16px;
  margin-top: 50px;
  padding-top: 24px;
  border-top: 1px solid var(--border-subtle);
  line-height: 1.7;
}

/* Loading Box */
#loading-overlay {
  display: none;
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(15, 23, 42, 0.88);
  z-index: 9999;
  justify-content: center;
  align-items: center;
  color: #ffffff;
  flex-direction: column;
  gap: 20px;
}

.loading-box {
  background: #ffffff;
  color: var(--text-primary);
  padding: 38px 46px;
  border-radius: var(--radius-md);
  text-align: center;
  max-width: 560px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
}

.loading-box h3 {
  font-size: 24px;
  color: var(--tbd-navy);
  margin-bottom: 12px;
}

.loading-box p {
  font-size: 17px;
  color: var(--text-secondary);
  line-height: 1.7;
}

@media (max-width: 800px) {
  .results-grid { grid-template-columns: 1fr; }
  .grid-2 { grid-template-columns: 1fr; }
  .header-top { flex-direction: column; align-items: flex-start; }
}
"""


def _document(content: str, *, active_tab: str = "analyze", subtitle: str = "") -> str:
    if not subtitle:
        subtitles = {
            "analyze": "İngilizce bilişim makalelerindeki teknik terimleri TBD Bilişim Sözlüğü ile denetleyiniz.",
            "dictionary": "TBD Bilişim Terimleri Sözlüğü ve Kısaltmalar veritabanını inceleyiniz.",
            "settings": "Bulut API sağlayıcısını ve model parametrelerini yapılandırınız.",
        }
        subtitle = subtitles.get(active_tab, "")

    nav = f"""
    <div class="nav-tabs">
      <a href="/" class="{'active' if active_tab == 'analyze' else ''}">Makale Analizi</a>
      <a href="/dictionary" class="{'active' if active_tab == 'dictionary' else ''}">Sözlük Yönetimi</a>
      <a href="/settings" class="{'active' if active_tab == 'settings' else ''}">API Ayarları</a>
    </div>
    """

    return f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Türkçe Terim Etmeni — TBD Bilişim</title>
  <style>{STYLE}</style>
</head>
<body>
  <header class="app-header">
    <div class="wrap">
      <div class="header-top">
        <div class="header-title-block">
          <div class="institution">Türkiye Bilişim Derneği</div>
          <h1>Türkçe Terim Etmeni</h1>
        </div>
        {nav}
      </div>
      <p class="header-description">{html.escape(subtitle)}</p>
    </div>
  </header>

  <main class="wrap main-content">
    {content}
    <div class="footer">
      Son karar insan incelemesiyle verilir; sözlük otomatik değiştirilmez.
      <br>
      Türkiye Bilişim Derneği (TBD) Bilişimde Özenli Türkçe Çalışma Grubu için hazırlanmıştır.
    </div>
  </main>

  <div id="loading-overlay">
    <div class="loading-box">
      <h3>Belge Analiz Ediliyor</h3>
      <p>Makale metni inceleniyor, teknik terimler çıkarılıyor ve güncel TBD sözlük kayıtları ile karşılaştırılıyor. Lütfen bekleyiniz...</p>
    </div>
  </div>

  <script>
    function showLoading() {{
      var overlay = document.getElementById('loading-overlay');
      if (overlay) overlay.style.display = 'flex';
    }}

    function displayChosenFile(input) {{
      var banner = document.getElementById('file-chosen-banner');
      var nameSpan = document.getElementById('file-chosen-name');
      if (input.files && input.files[0]) {{
        if (nameSpan) nameSpan.textContent = input.files[0].name;
        if (banner) banner.style.display = 'block';
      }}
    }}

    function filterTerms(group) {{
      var items = document.querySelectorAll('.term-entry');
      var pills = document.querySelectorAll('.filter-btn');
      pills.forEach(function(p) {{ p.classList.remove('active'); }});
      if (window.event && window.event.target && window.event.target.classList) {{
        window.event.target.classList.add('active');
      }}

      var query = (document.getElementById('term-search')?.value || '').toLowerCase();

      items.forEach(function(item) {{
        var itemGroup = item.getAttribute('data-group');
        var termText = item.querySelector('.term-heading')?.textContent.toLowerCase() || '';
        var matchGroup = (group === 'all' || itemGroup === group);
        var matchQuery = (!query || termText.includes(query));
        item.style.display = (matchGroup && matchQuery) ? 'block' : 'none';
      }});
    }}

    function searchTerms() {{
      var activePill = document.querySelector('.filter-btn.active');
      var group = activePill ? activePill.getAttribute('data-filter') : 'all';
      filterTerms(group);
    }}
  </script>
</body>
</html>"""


def _status_card(service: AnalysisService) -> str:
    status = service.dictionary_status()
    return f"""
    <div class="dict-status-strip">
      <div class="dict-status-info">
        <span class="dict-title">Güncel sözlük: {html.escape(status.version)}</span>
        <span class="dict-counts">{status.record_count:,} kayıt · {status.unique_count:,} benzersiz İngilizce terim</span>
      </div>
      <a class="btn btn-secondary btn-sm" href="/dictionary">Sözlüğü yönet</a>
    </div>
    """


def index_html(service: AnalysisService, message: str = "", message_type: str = "failed") -> str:
    notice_cls = "notice-ok" if message_type == "ok" else ("notice-warn" if message_type == "current" else "notice-danger")
    notice = f'<div class="notice {notice_cls}">{html.escape(message)}</div>' if message else ""

    if service.using_api():
        status = service.provider_status()
        if not status["has_key"]:
            notice += '<div class="notice notice-warn"><b>Bulut API anahtarı girilmemiş.</b> <a href="/settings" style="color:inherit; font-weight:700;">API Ayarları</a> sayfasından anahtarınızı kaydediniz.</div>'
        
        provider_title = "Google (Gemini)" if status["provider"] == "google" else status["provider"].title()
        engine_info = f"""
        <div class="active-engine-badge">
          <div class="engine-status-text">
            <span class="engine-status-dot"></span>
            <span>Çalışma Modu: <b>Bulut API</b> — {html.escape(provider_title)} (<code>{html.escape(status['model'])}</code>)</span>
          </div>
          <a class="btn btn-secondary btn-sm" href="/settings">Modeli Değiştir</a>
        </div>
        """
        model_field = ""
    else:
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
        if not models:
            options = '<option value="">Ollama modeli bulunamadı</option>'
        if model_error:
            notice += f'<div class="notice notice-danger"><b>Analiz motoruna bağlanılamadı.</b> {html.escape(model_error)}</div>'

        engine_info = """
        <div class="active-engine-badge">
          <div class="engine-status-text">
            <span class="engine-status-dot"></span>
            <span>Çalışma Modu: <b>Yerel Ollama</b> (Cihazınızdaki yerel model)</span>
          </div>
          <a class="btn btn-secondary btn-sm" href="/settings">Bulut API'ye Geç</a>
        </div>
        """
        model_field = f"""
        <div class="form-group" style="margin-top:20px;">
          <label for="model-select">Yerel analiz modeli</label>
          <select id="model-select" name="model" required>
            {options}
          </select>
        </div>
        """

    content = f"""
    {notice}
    {_status_card(service)}

    <section class="card">
      <h2 class="card-title">Makale analizi</h2>
      <p class="card-intro">Metin katmanı bulunan İngilizce PDF'yi seçin. Sonuçta önce sözlükte bulunmayan terimler gösterilir.</p>

      {engine_info}

      <form action="/analyze" method="post" enctype="multipart/form-data" onsubmit="showLoading()">
        <div class="upload-zone">
          <label class="upload-label-title" for="pdf-input">Makale PDF'si</label>
          <span class="upload-hint">İncelemek istediğiniz İngilizce bilimsel makaleyi seçiniz (Yalnızca .pdf formatı)</span>
          <input type="file" id="pdf-input" class="file-input-field" name="pdf" accept="application/pdf,.pdf" required onchange="displayChosenFile(this)">
          <div id="file-chosen-banner" class="file-chosen-banner" style="display:none;">
            <b>Seçilen Dosya:</b> <span id="file-chosen-name"></span>
          </div>
        </div>

        {model_field}

        <div style="margin-top:24px;">
          <button class="btn btn-primary btn-lg" type="submit">
            Eksik terimleri bul
          </button>
        </div>
      </form>
    </section>
    """
    return _document(content, active_tab="analyze")


def result_html(result: dict[str, object], links: dict[str, str]) -> str:
    missing = [item for item in result.get("missing_terms", []) if isinstance(item, dict)]
    possible = [item for item in result.get("possible_matches", []) if isinstance(item, dict)]
    found = [item for item in result.get("dictionary_matches", []) if isinstance(item, dict)]
    
    doc_name = str(result.get("document", "Belge"))
    model_name = str(result.get("model", "Model"))
    dict_version = str(result.get("dictionary_version", ""))
    status = str(result.get("analysis_status", "complete"))
    warnings_list = result.get("processing_warnings", [])
    first_warn = str(warnings_list[0]) if isinstance(warnings_list, list) and warnings_list else ""

    if status == "failed":
        detail_msg = f"<div style='background:#fef2f2; border:1px solid #fca5a5; border-radius:var(--radius-sm); padding:14px 18px; margin:16px 0 20px; color:#991b1b; font-size:14px; word-break:break-word;'><b>Hata Ayrıntısı:</b> {html.escape(first_warn or 'Bilinmeyen bağlantı veya model hatası.')}</div>" if first_warn else ""
        content = f"""
        <div class="card" style="border-left: 4px solid var(--danger-text); padding: 24px 28px;">
          <h2 style="color:var(--danger-text); font-size:20px; margin-bottom:10px;">Analiz Tamamlanamadı</h2>
          <p style="font-size:15px; color:var(--text-secondary); line-height:1.7;">
            Model veya API sağlayıcısı belgeyi işleyemediği için analiz tamamlanamadı. <b>Bu sonuç “0 eksik terim” olarak yorumlanmamalıdır.</b> Hatalı durum için boş/geçersiz rapor dosyası üretilmemiştir.
          </p>
          {detail_msg}
          <div style="font-size:14px; color:var(--text-secondary); margin-bottom:20px; line-height:1.6;">
            <b>Önerilen İşlem:</b> Eğer API hatası (401 Yetkilendirme, 404 Model Bulunamadı veya 429 Kota Aşımı) aldıysanız, lütfen <b>API Ayarları</b> sayfasından seçtiğiniz sağlayıcıyı ve API anahtarınızı kontrol ediniz.
          </div>
          <div style="display:flex; gap:12px; flex-wrap:wrap;">
            <a class="btn btn-primary btn-sm" href="/settings">API Ayarlarını Kontrol Et</a>
            <a class="btn btn-secondary btn-sm" href="/">Yeni Belge Yükle</a>
          </div>
        </div>
        """
        return _document(content, active_tab="analyze", subtitle=f"Analiz Başarısız: {html.escape(doc_name)}")

    warning = ""
    if status != "complete":
        detail_msg = f"<br><span style='color:var(--danger-text); font-size:13px; display:block; margin-top:4px;'><b>Hata Ayrıntısı:</b> {html.escape(first_warn)}</span>" if first_warn else ""
        warning = '<div class="notice notice-warn"><b>Analiz {}.</b> Bu sonuç “0 eksik terim” olarak yorumlanmamalıdır.{}</div>'.format(
            "kısmi tamamlandı" if status == "partial" else "tamamlanamadı", detail_msg
        )


    # Render Entries
    entries_html = []
    
    # 1. Missing Terms (İnceleme Gerekli)
    for item in missing:
        term = str(item.get("term", ""))
        context = str(item.get("context", ""))
        pages = ", ".join(str(p) for p in item.get("pages", []))
        count = str(item.get("occurrence_count", 1))
        entries_html.append(f"""
        <div class="term-entry" data-group="missing">
          <div class="term-top">
            <span class="term-heading">{html.escape(term)}</span>
            <span class="badge badge-missing">Sözlükte Bulunmayan Terim</span>
          </div>
          {f'<div class="term-context-box"><b>Metin Bağlamı:</b> “{html.escape(context)}”</div>' if context else ''}
          <div class="term-meta-info">
            <span>Sayfa Numaraları: {html.escape(pages or '-')}</span>
            <span>Metindeki Geçiş Sayısı: {count}</span>
          </div>
        </div>
        """)

    # 2. Possible Matches / Abbreviations
    for item in possible:
        term = str(item.get("term", ""))
        context = str(item.get("context", ""))
        pages = ", ".join(str(p) for p in item.get("pages", []))
        count = str(item.get("occurrence_count", 1))
        suggestions = item.get("possible_dictionary_terms", [])
        expansions = " | ".join(
            f"{v.get('en', '')} → {v.get('tr', '')}" for v in suggestions if isinstance(v, dict)
        ) if isinstance(suggestions, list) else ""

        entries_html.append(f"""
        <div class="term-entry" data-group="abbrev">
          <div class="term-top">
            <span class="term-heading">{html.escape(term)}</span>
            <span class="badge badge-abbrev">Kısaltma kaynağında</span>
          </div>
          {f'<div style="font-size:14px; color:var(--warning-text); margin-bottom:8px;"><b>Kısaltma Açılımı ve Karşılığı:</b> {html.escape(expansions)}</div>' if expansions else ''}
          {f'<div class="term-context-box"><b>Metin Bağlamı:</b> “{html.escape(context)}”</div>' if context else ''}
          <div class="term-meta-info">
            <span>Sayfa Numaraları: {html.escape(pages or '-')}</span>
            <span>Metindeki Geçiş Sayısı: {count}</span>
          </div>
        </div>
        """)

    # 3. Found Terms
    for item in found:
        term = str(item.get("term", ""))
        translations = ", ".join(str(t) for t in item.get("translations", []))
        pages = ", ".join(str(p) for p in item.get("pages", []))
        count = str(item.get("occurrence_count", 1))
        match_type = str(item.get("match_type", "exact"))
        tag_label = "Sözlükte Kayıtlı" if match_type == "exact" else "Sözlükte Kayıtlı (Çoğul Eşleşme)"

        entries_html.append(f"""
        <div class="term-entry" data-group="found">
          <div class="term-top">
            <span class="term-heading">{html.escape(term)}</span>
            <span class="badge badge-found">{tag_label}</span>
          </div>
          <div style="font-size:15px; color:var(--success-text); font-weight:700; margin-bottom:6px;">
            Türkçe Karşılık: {html.escape(translations)}
          </div>
          <div class="term-meta-info">
            <span>Sayfa Numaraları: {html.escape(pages or '-')}</span>
            <span>Metindeki Geçiş Sayısı: {count}</span>
          </div>
        </div>
        """)

    rendered_entries = "".join(entries_html) if entries_html else '<p style="color:var(--text-muted); text-align:center; padding:20px;">İncelenecek terim bulunamadı.</p>'

    content = f"""
    {warning}

    <div class="summary-table-wrap">
      <table class="summary-table">
        <thead>
          <tr>
            <th>İnceleme Gereken (Eksik Terim)</th>
            <th>TBD Kısaltma Kaynağında</th>
            <th>Sözlükte Bulunan Terimler</th>
            <th>Toplam Çıkarılan Terim</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="color:#b91c1c; font-weight:700; font-size:28px;">{len(missing)}</td>
            <td style="color:#b45309; font-weight:700; font-size:28px;">{len(possible)}</td>
            <td style="color:#15803d; font-weight:700; font-size:28px;">{len(found)}</td>
            <td style="font-weight:700; font-size:28px; color:#0f2942;">{len(missing) + len(possible) + len(found)}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="results-grid">
      <div>
        <div class="filter-bar">
          <input type="text" id="term-search" class="filter-input" placeholder="Sonuç listesinde terim arayınız..." oninput="searchTerms()">
          <div class="filter-tabs">
            <button class="filter-btn active" data-filter="all" onclick="filterTerms('all')">Tümü ({len(missing) + len(possible) + len(found)})</button>
            <button class="filter-btn" data-filter="missing" onclick="filterTerms('missing')">Eksikler ({len(missing)})</button>
            <button class="filter-btn" data-filter="abbrev" onclick="filterTerms('abbrev')">Kısaltmalar ({len(possible)})</button>
            <button class="filter-btn" data-filter="found" onclick="filterTerms('found')">Bulunanlar ({len(found)})</button>
          </div>
        </div>

        <div class="term-list">
          {rendered_entries}
        </div>
      </div>

      <aside>
        <div class="card" style="padding:28px 24px;">
          <h3 style="font-size:18px; font-weight:700; color:var(--tbd-navy); margin-bottom:16px; border-bottom:2px solid var(--border-subtle); padding-bottom:8px;">
            Rapor Dosyaları
          </h3>
          <div class="export-panel">
            <a class="btn btn-primary btn-block" href="/reports/{urllib.parse.quote(links['xlsx'])}" style="font-size:16px; padding:12px 18px;">Excel Raporunu İndir (.xlsx)</a>
            <a class="btn btn-secondary btn-block" href="/reports/{urllib.parse.quote(links['csv'])}" style="font-size:15px; padding:11px 18px;">CSV Raporunu İndir (.csv)</a>
            <a class="btn btn-secondary btn-block" href="/reports/{urllib.parse.quote(links['json'])}" style="font-size:15px; padding:11px 18px;">Teknik JSON Dosyası (.json)</a>
          </div>

          <hr style="border:0; border-top:1px solid var(--border-subtle); margin:22px 0;">

          <div style="font-size:15px; color:var(--text-secondary); line-height:1.8;">
            <div><b>İncelenen Belge:</b> {html.escape(doc_name)}</div>
            <div><b>Analiz Modeli:</b> {html.escape(model_name)}</div>
            <div><b>TBD Sözlük Sürümü:</b> {html.escape(dict_version)}</div>
          </div>

          <a class="btn btn-secondary btn-block" href="/" style="margin-top:22px; font-size:16px; font-weight:700; padding:12px 18px;">Yeni Belge İncele</a>
        </div>
      </aside>
    </div>
    """
    return _document(content, active_tab="analyze", subtitle=f"İnceleme Sonuçları: {html.escape(doc_name)}")


def dictionary_html(service: AnalysisService, message: str = "", message_type: str = "ok") -> str:
    status = service.dictionary_status()
    abbreviation_status = service.abbreviations.metadata
    notice_cls = "notice-ok" if message_type == "ok" else "notice-danger"
    notice = f'<div class="notice {notice_cls}">{html.escape(message)}</div>' if message else ""

    content = f"""
    {notice}

    <div class="grid-2">
      <section class="card">
        <h2 class="card-title">Etkin Sözlük</h2>
        <p class="card-intro">İngilizce → Türkçe ana bilişim sözlüğü veritabanı.</p>
        
        <div style="font-size:17px; line-height:2.0; margin-bottom:28px;">
          <div><b>Sözlük Sürümü:</b> {html.escape(status.version)}</div>
          <div><b>Toplam Terim Kaydı:</b> {status.record_count:,}</div>
          <div><b>Benzersiz İngilizce Terim:</b> {status.unique_count:,}</div>
          <div><b>Kaynak:</b> {html.escape(status.source)}</div>
        </div>

        <form action="/dictionary/check" method="post">
          <button class="btn btn-primary" type="submit">TBD sitesini kontrol et</button>
        </form>
      </section>

      <section class="card">
        <h2 class="card-title">Ayrı kısaltma kaynağı</h2>
        <p class="card-intro">Resmî TBD Kısaltmalar tablosu veritabanı.</p>

        <div style="font-size:17px; line-height:2.0; margin-bottom:28px;">
          <div><b>Kısaltma Sürümü:</b> {html.escape(str(abbreviation_status.get('version', '')))}</div>
          <div><b>Okunan Kayıt Sayısı:</b> {int(abbreviation_status.get('raw_record_count', 0)):,}</div>
          <div><b>Benzersiz Kısaltma Sayısı:</b> {int(abbreviation_status.get('unique_abbreviation_count', 0)):,}</div>
        </div>
        <p style="font-size:15px; color:var(--text-muted);">Ana sözlüğe birleştirilmez; eşleşmeler raporda kaynak etiketiyle gösterilir.</p>
      </section>
    </div>

    <section class="card">
      <h2 class="card-title">Sözlük PDF'sini elle yükle</h2>
      <p class="card-intro">Site otomatik erişime izin vermezse resmî İngilizce–Türkçe PDF burada doğrulanabilir.</p>

      <form action="/dictionary/import" method="post" enctype="multipart/form-data">
        <div class="form-group">
          <label for="dict-pdf">TBD Sözlük PDF Belgesi Seçiniz</label>
          <input type="file" id="dict-pdf" name="dictionary" class="file-input-field" accept="application/pdf,.pdf" required>
        </div>
        <button class="btn btn-secondary btn-sm" type="submit" style="margin-top:10px;">Doğrula ve etkinleştir</button>
      </form>
    </section>
    """
    return _document(content, active_tab="dictionary")


def settings_html(service: AnalysisService, message: str = "", message_type: str = "ok") -> str:
    status = service.provider_status()
    notice_cls = "notice-ok" if message_type == "ok" else "notice-danger"
    notice = f'<div class="notice {notice_cls}">{html.escape(message)}</div>' if message else ""

    providers = [
        ("google", "Google (Gemini)"),
        ("deepseek", "DeepSeek"),
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic (Claude)"),
        ("ollama", "Yerel Ollama (Cihazdaki Yerel Model)"),
    ]
    provider_options = "".join(
        f'<option value="{name}"{" selected" if name == status["provider"] else ""}>{label}</option>'
        for name, label in providers
    )
    key_note = "Kayıtlı bir anahtar var (korunuyor)." if status["has_key"] else "Henüz anahtar girilmedi."
    key_placeholder = "•••••••••••••••• (Kayıtlı anahtar korunuyor; değiştirmek için yeni giriniz)" if status["has_key"] else "API anahtarını buraya giriniz"

    key_status_badge = '<span style="color:#15803d; font-weight:700;">● Kayıtlı ve Hazır</span>' if status["has_key"] else '<span style="color:#b91c1c; font-weight:700;">○ Girilmedi</span>'
    provider_title = "Google (Gemini)" if status["provider"] == "google" else status["provider"].title()

    content = f"""
    {notice}

    <section class="card">
      <h2 class="card-title">Bulut API Ayarları</h2>
      <p class="card-intro">Kullandığınız yapay zekâ sağlayıcısını, model adını ve API anahtarınızı buradan yönetebilirsiniz.</p>

      <div class="current-config-grid">
        <div class="config-stat-card">
          <span class="config-stat-label">Aktif Sağlayıcı</span>
          <span class="config-stat-value">{html.escape(provider_title)}</span>
        </div>
        <div class="config-stat-card">
          <span class="config-stat-label">Seçili Model</span>
          <span class="config-stat-value"><code>{html.escape(status['model'])}</code></span>
        </div>
        <div class="config-stat-card">
          <span class="config-stat-label">API Anahtarı Durumu</span>
          <span class="config-stat-value">{key_status_badge}</span>
        </div>
      </div>

      <form action="/settings/save" method="post">
        <div class="grid-2">
          <div class="form-group">
            <label for="provider-select">Sağlayıcı</label>
            <select id="provider-select" name="provider" required>
              {provider_options}
            </select>
          </div>

          <div class="form-group">
            <label for="model-input">Model Adı</label>
            <input type="text" id="model-input" name="model" value="{html.escape(status['model'], quote=True)}" placeholder="Kullanmak istediğiniz güncel model adı">
            <span style="font-size:15px; color:var(--text-muted); display:block; margin-top:6px;">Hesabınızda tanımlı olan güncel model adını yazınız.</span>
          </div>

          <div class="form-group">
            <label for="key-input">API Anahtarı</label>
            <input type="password" id="key-input" name="api_key" value="" placeholder="{key_placeholder}">
            <span style="font-size:15px; color:var(--text-muted); display:block; margin-top:6px;">Değiştirmek istemiyorsanız bu alanı boş bırakabilirsiniz.</span>
          </div>

          <div class="form-group">
            <label for="url-input">Sunucu Adresi (İsteğe bağlı)</label>
            <input type="text" id="url-input" name="base_url" value="{html.escape(status.get('custom_base_url', ''), quote=True)}" placeholder="Boş bırakılırsa sağlayıcının resmî adresi kullanılır">
            <span style="font-size:15px; color:var(--text-muted); display:block; margin-top:6px;">Boş bırakıldığında doğrudan resmî bulut adresi kullanılır. Yalnızca özel vekil sunucu varsa yazınız.</span>
          </div>
        </div>

        <div style="background:#f8fafc; border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:20px 24px; margin: 20px 0 28px;">
          <b style="font-size:17px; display:block; margin-bottom:10px; color:var(--tbd-navy);">Sağlayıcıların Resmî Dokümantasyon Sayfaları:</b>
          <p style="font-size:15px; color:var(--text-secondary); margin-bottom:12px; line-height:1.7;">
            Yapay zekâ sağlayıcıları model isimlerini zamanla güncelleyebilir. Hesabınızın desteklediği güncel modeller için resmî bağlantıları inceleyebilirsiniz:
          </p>
          <ul style="font-size:16px; line-height:2.0; padding-left:24px; color:var(--text-secondary);">
            <li><b>DeepSeek API:</b> <a href="https://api-docs.deepseek.com/" target="_blank" rel="noopener">https://api-docs.deepseek.com/</a></li>
            <li><b>OpenAI API:</b> <a href="https://platform.openai.com/docs/models" target="_blank" rel="noopener">https://platform.openai.com/docs/models</a></li>
            <li><b>Anthropic Claude API:</b> <a href="https://docs.anthropic.com/en/docs/about-claude/models" target="_blank" rel="noopener">https://docs.anthropic.com/en/docs/about-claude/models</a></li>
            <li><b>Google Gemini API:</b> <a href="https://ai.google.dev/gemini-api/docs/models/gemini" target="_blank" rel="noopener">https://ai.google.dev/gemini-api/docs/models/gemini</a></li>
          </ul>
        </div>

        <button class="btn btn-primary btn-lg" type="submit">Ayarları Kaydet</button>
      </form>
    </section>
    """
    return _document(content, active_tab="settings", subtitle="Analiz modeli sağlayıcı ayarları")




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


class Server(ThreadingHTTPServer):
    def __init__(self, address, service: AnalysisService) -> None:
        self.service = service
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server: Server

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path == "/healthz":
            self._health(); return
        if path == "/":
            self._html(index_html(self.server.service)); return
        if path == "/dictionary":
            self._html(dictionary_html(self.server.service)); return
        if path == "/settings":
            self._html(settings_html(self.server.service)); return
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
                    "json": str(json_path.relative_to(base)) if json_path.name and json_path.is_file() else "",
                    "csv": str(csv_path.relative_to(base)) if csv_path.name and csv_path.is_file() else "",
                    "xlsx": str(xlsx_path.relative_to(base)) if xlsx_path.name and xlsx_path.is_file() else "",
                }
                self._html(result_html(result, links)); return
            if path == "/settings/save":
                fields = _urlencoded(self)
                from .provider_store import ProviderConfig
                existing = self.server.service.provider_store.load()
                submitted_key = fields.get("api_key", "").strip()
                final_key = submitted_key if submitted_key else existing.api_key
                config = ProviderConfig(
                    provider=fields.get("provider", "openai"),
                    api_key=final_key,
                    model=fields.get("model", "").strip(),
                    base_url=fields.get("base_url", "").strip(),
                )
                self.server.service.save_provider_config(config)
                self._html(settings_html(self.server.service, "API ayarları kaydedildi.", "ok")); return
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
            "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; form-action 'self'; "
            "frame-ancestors 'none'; base-uri 'none'",
        )

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
    server = Server((host, port), service)
    url_host = "[{}]".format(host) if ":" in host else host
    url = "http://{}:{}".format(url_host, port)
    print("Türkiye Bilişim Derneği — Bilişim Terimleri Denetim Sistemi: {}".format(url), flush=True)
    print("Durdurmak için Control-C tuşlarına basınız.", flush=True)
    if open_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSistem kapatıldı.")
    finally:
        server.server_close()
