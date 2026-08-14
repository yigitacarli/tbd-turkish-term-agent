"""Birden çok bulut sağlayıcısını destekleyen terim adayı üreticisi.

OpenAI, DeepSeek, Anthropic ve Google (Gemini) için tek ortak arayüz sağlar.
İstemler ve JSON ayrıştırma mantığı ``terim_etmeni.ollama_client`` içinden yeniden
kullanılır; yalnızca HTTP istek biçimi ve yanıt ayrıştırma sağlayıcıya göre değişir.

Sağlayıcı yalnız aday üretir; sözlük üyeliği kararını deterministik katman verir
(ADR-002).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from terim_etmeni.models import ExtractedTerm
from terim_etmeni.ollama_client import (
    DISCOVERY_TASK,
    SYSTEM_PROMPT,
    TERM_REVIEW_SYSTEM,
    TERM_REVIEW_TASK,
    USER_TASK,
    _json_from_text,
)


# Sağlayıcı varsayılanları: (adres, varsayılan model, tür)
PROVIDER_DEFAULTS = {
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
    "anthropic": ("https://api.anthropic.com", "claude-sonnet-4-20250514"),
    "google": ("https://generativelanguage.googleapis.com", "gemini-2.0-flash"),
}

_ANTHROPIC_VERSION = "2023-06-01"


class ApiClientError(RuntimeError):
    pass


def provider_base_url(provider: str) -> str:
    return PROVIDER_DEFAULTS.get(provider, (provider, ""))[0]


def provider_default_model(provider: str) -> str:
    return PROVIDER_DEFAULTS.get(provider, ("", ""))[1]


class ApiClient:
    """OpenAI-uyumlu, Anthropic veya Google API üzerinden aday üreten istemci."""

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        base_url: str = "",
        timeout: int = 240,
        review_passes: int = 1,
    ) -> None:
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or provider_base_url(provider)).rstrip("/")
        self.timeout = timeout
        if review_passes not in (1, 2):
            raise ValueError("İnceleme geçişi sayısı 1 veya 2 olmalı.")
        self.review_passes = review_passes

    def installed_models(self) -> list[str]:
        return [self.model] if self.model else []

    def check_model(self) -> None:
        if not self.model:
            raise ApiClientError("API modeli ayarlanmamış.")

    def extract(self, text: str) -> list[ExtractedTerm]:
        output: list[ExtractedTerm] = []
        seen: set[str] = set()
        templates = (USER_TASK, DISCOVERY_TASK) if self.review_passes == 2 else (USER_TASK,)
        for template in templates:
            user_prompt = template.format(text=text)
            for extracted in self._extract_prompt(user_prompt):
                key = extracted.term.casefold()
                if key not in seen:
                    seen.add(key)
                    output.append(extracted)
        return output

    def validate_terms(self, terms: list[str]) -> list[str]:
        unique = list(dict.fromkeys(term for term in terms if term.strip()))
        accepted: list[str] = []
        for start in range(0, len(unique), 30):
            batch = unique[start : start + 30]
            prompt = TERM_REVIEW_TASK.format(
                candidates="\n".join("- " + term for term in batch)
            )
            returned = self._extract_prompt(
                prompt, system=TERM_REVIEW_SYSTEM, max_tokens=1024
            )
            allowed = {term.casefold(): term for term in batch}
            for item in returned:
                exact = allowed.get(item.term.casefold())
                if exact and exact not in accepted:
                    accepted.append(exact)
        return accepted

    def _extract_prompt(
        self,
        user_prompt: str,
        system: str = SYSTEM_PROMPT,
        max_tokens: int = 256,
    ) -> list[ExtractedTerm]:
        last_error: Exception | None = None
        parsed: dict[str, object] | None = None
        for attempt in range(2):
            retry_instruction = "Return one complete JSON object only. Do not add commentary."
            effective_prompt = (
                user_prompt if not attempt else retry_instruction + "\n\n" + user_prompt
            )
            try:
                content = self._chat(system, effective_prompt, max_tokens)
            except ApiClientError as error:
                last_error = error
                continue
            if not content.strip():
                last_error = ApiClientError("Model boş yanıt döndürdü.")
                continue
            try:
                parsed = _json_from_text(content)
                break
            except Exception as error:
                last_error = error
        if parsed is None:
            raise last_error or ApiClientError("Model geçerli JSON döndürmedi.")
        raw_terms = parsed.get("terms")
        if not isinstance(raw_terms, list):
            raise ApiClientError("Model yanıtında 'terms' listesi bulunamadı.")

        output: list[ExtractedTerm] = []
        for item in raw_terms:
            if isinstance(item, str):
                term = item.strip()
            elif isinstance(item, dict):
                value = item.get("term")
                term = value.strip() if isinstance(value, str) else ""
            else:
                continue
            if term:
                output.append(ExtractedTerm(term=term))
        return output

    def _chat(self, system: str, user_prompt: str, max_tokens: int) -> str:
        if self.provider == "anthropic":
            return self._anthropic_chat(system, user_prompt, max_tokens)
        if self.provider == "google":
            return self._google_chat(system, user_prompt, max_tokens)
        return self._openai_compatible_chat(system, user_prompt, max_tokens)

    def _openai_compatible_chat(self, system: str, user_prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        result = self._request(
            self.base_url + "/chat/completions",
            payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.api_key),
            },
        )
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ApiClientError("API yanıtında 'choices' bulunamadı.")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ApiClientError("API yanıtında 'message' bulunamadı.")
        content = message.get("content")
        if not isinstance(content, str):
            raise ApiClientError("API yanıtında 'content' bulunamadı.")
        return content

    def _anthropic_chat(self, system: str, user_prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.model,
            "system": system,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": max_tokens,
        }
        result = self._request(
            self.base_url + "/v1/messages",
            payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
            },
        )
        content = result.get("content")
        if not isinstance(content, list) or not content:
            raise ApiClientError("API yanıtında 'content' bulunamadı.")
        text = ""
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                text += block["text"]
        if not text:
            raise ApiClientError("API yanıtında metin bulunamadı.")
        return text

    def _google_chat(self, system: str, user_prompt: str, max_tokens: int) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens},
        }
        endpoint = "/v1beta/models/{}:generateContent".format(self.model)
        if "?" in endpoint:
            endpoint += "&"
        else:
            endpoint += "?"
        endpoint += "key=" + urllib.parse.quote(self.api_key)
        result = self._request(
            self.base_url + endpoint,
            payload,
            headers={"Content-Type": "application/json"},
        )
        candidates = result.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ApiClientError("API yanıtında 'candidates' bulunamadı.")
        candidate = candidates[0]
        if not isinstance(candidate, dict):
            raise ApiClientError("API yanıt biçimi beklenenden farklı.")
        content = candidate.get("content", {})
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text = ""
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text += part["text"]
        if not text:
            raise ApiClientError("API yanıtında metin bulunamadı.")
        return text

    def _request(
        self, url: str, payload: dict[str, object], headers: dict[str, str]
    ) -> dict[str, object]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ApiClientError(
                "API HTTP hatası {}: {}".format(error.code, detail)
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ApiClientError("API'ye bağlanılamadı.") from error
        except json.JSONDecodeError as error:
            raise ApiClientError("API geçersiz bir HTTP yanıtı döndürdü.") from error
        if not isinstance(result, dict):
            raise ApiClientError("API yanıtının biçimi beklenenden farklı.")
        return result
