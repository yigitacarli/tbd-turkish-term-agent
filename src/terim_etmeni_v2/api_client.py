"""OpenAI uyumlu bulut API'si üzerinden terim adayı üreten sağlayıcı.

Yerel Ollama istemcisiyle aynı ``TermProvider`` arayüzünü uygular; yalnızca
istek taşıma katmanı farklıdır. İstemler ve JSON ayrıştırma mantığı
``terim_etmeni.ollama_client`` içinden yeniden kullanılır, böylece modelin aday
üretme ve teknik inceleme davranışı iki sağlayıcıda da aynı kalır.

Sözlük üyeliği kararını bu sağlayıcı vermez; yalnızca aday üretir (ADR-002).
"""
from __future__ import annotations

import json
import urllib.error
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


class ApiClientError(RuntimeError):
    pass


class ApiClient:
    """OpenAI uyumlu ``/chat/completions`` bitiş noktasını konuşan aday üretici."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        timeout: int = 240,
        review_passes: int = 1,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        if review_passes not in (1, 2):
            raise ValueError("İnceleme geçişi sayısı 1 veya 2 olmalı.")
        self.review_passes = review_passes

    def installed_models(self) -> list[str]:
        # Bulut API'sinde "kurulu model" listesi yoktur; ayarlanan model tek seçenektir.
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
        """Adayların teknik terim niteliğini bulut modeliyle temkinli doğrular."""
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
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        last_error: Exception | None = None
        parsed: dict[str, object] | None = None
        for attempt in range(2):
            retry_instruction = "Return one complete JSON object only. Do not add commentary."
            effective_prompt = (
                user_prompt if not attempt else retry_instruction + "\n\n" + user_prompt
            )
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": effective_prompt},
            ]
            request_payload = dict(payload)
            request_payload["messages"] = messages
            try:
                content = self._chat(request_payload)
            except ApiClientError as error:
                last_error = error
                continue
            if not content.strip():
                last_error = ApiClientError("Model boş yanıt döndürdü.")
                continue
            try:
                parsed = _json_from_text(content)
                break
            except Exception as error:  # JSON ayrıştırma hatası -> yeniden dene
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

    def _chat(self, payload: dict[str, object]) -> str:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.api_key),
            },
            method="POST",
        )
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
