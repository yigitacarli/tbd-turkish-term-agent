"""Uzak TBD kaynağını güvenli biçimde kontrol etme."""
from __future__ import annotations

import html as html_module
import json
import re
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .dictionary_pdf import DictionaryImportError
from .dictionary_store import DictionaryStatus, DictionaryStore


@dataclass(frozen=True)
class UpdateResult:
    status: str
    message: str
    dictionary: DictionaryStatus


_PDF_PATTERNS = (
    re.compile(r"https?://[^\"'<>\s]+\.pdf(?:\?[^\"'<>\s]*)?", re.I),
    re.compile(r"(?:src|href|file|url)=[\"']([^\"']+\.pdf(?:\?[^\"']*)?)[\"']", re.I),
)


def _request(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Turkce-Terim-Etmeni/1.0 (+dictionary-update)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def discover_pdf_url(page_url: str, timeout: int = 25) -> str:
    html = _request(page_url, timeout).decode("utf-8", errors="replace")
    # WordPress PDF Poster eklentisi gerçek sözlük dosyasını JSON biçimli
    # data-attributes alanında tutuyor. Sayfanın menüsündeki çalışma raporları
    # ilk PDF bağlantıları olduğu için önce bu yapılandırmayı okumalıyız.
    for encoded in re.findall(r"data-attributes='([^']+)'", html, flags=re.I):
        try:
            attributes = json.loads(html_module.unescape(encoded))
        except (TypeError, json.JSONDecodeError):
            continue
        value = attributes.get("file") if isinstance(attributes, dict) else None
        if isinstance(value, str) and ".pdf" in value.casefold():
            joined = urllib.parse.urljoin(page_url, value)
            return urllib.parse.quote(joined, safe=":/?&=%")

    for pattern in _PDF_PATTERNS:
        match = pattern.search(html)
        if match:
            value = match.group(1) if match.lastindex else match.group(0)
            joined = urllib.parse.urljoin(page_url, value.replace("&amp;", "&"))
            return urllib.parse.quote(joined, safe=":/?&=%")
    raise DictionaryImportError(
        "Sözlük sayfasında doğrudan PDF bağlantısı bulunamadı. "
        "TBD_DICTIONARY_PDF_URL ayarıyla resmî dosya adresi verilebilir."
    )


def check_and_update(
    store: DictionaryStore,
    *,
    page_url: str,
    pdf_url: str = "",
    timeout: int = 25,
) -> UpdateResult:
    current = store.status()
    try:
        source_url = pdf_url or discover_pdf_url(page_url, timeout)
        payload = _request(source_url, timeout)
        if not payload.startswith(b"%PDF-"):
            raise DictionaryImportError("Uzak adres PDF yerine farklı bir içerik döndürdü.")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as target:
            target.write(payload)
            temporary = Path(target.name)
        try:
            updated = store.import_pdf(temporary)
        finally:
            temporary.unlink(missing_ok=True)
    except Exception as error:
        return UpdateResult(
            "failed",
            "Güncelleme doğrulanamadı; son sağlam sözlük korunuyor: {}".format(error),
            current,
        )
    if updated.path == current.path:
        return UpdateResult("current", "Sözlük zaten güncel.", updated)
    return UpdateResult(
        "updated",
        "{} sürümlü sözlük doğrulandı ve etkinleştirildi.".format(updated.version),
        updated,
    )
