"""Ollama HTTP API için küçük ve bağımsız istemci.

Yalnızca teknik terim adayı üretir; sözlük üyeliği kararını deterministik katman
verir (ADR-002). İstem metni :mod:`terim_etmeni.term_extraction` içindeki few-shot
şablondan gelir.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from terim_etmeni.models import ExtractedTerm
from terim_etmeni.term_extraction import OUTPUT_SCHEMA, SYSTEM_PROMPT, USER_TASK


class OllamaError(RuntimeError):
    pass


def _json_from_text(raw: str) -> dict[str, object]:
    value = raw.strip()
    # Markdown kod bloklarını ayıkla (örn. ```json ... ```)
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", value, flags=re.IGNORECASE)
    if code_block_match:
        value = code_block_match.group(1).strip()

    # Doğrudan ayrıştırmayı dene
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return {"terms": parsed}
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # İlk { veya [ ile son } veya ] arasını bul
    first_brace = value.find("{")
    last_brace = value.rfind("}")
    first_bracket = value.find("[")
    last_bracket = value.rfind("]")

    candidate = ""
    # Nesne ({...}) adayını kontrol et
    if first_brace >= 0 and last_brace > first_brace:
        candidate = value[first_brace : last_brace + 1]
    elif first_bracket >= 0 and last_bracket > first_bracket:
        candidate = value[first_bracket : last_bracket + 1]

    if candidate:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return {"terms": parsed}
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return {"terms": parsed}
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    # 4. Kesilmiş veya nesne tabanlı JSON'dan terimleri kurtarma adımı
    obj_terms = re.findall(r'"term"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', value)
    if obj_terms:
        return {"terms": [{"term": t} for t in obj_terms]}

    raise OllamaError("Model geçerli JSON döndürmedi.")





class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: int = 240) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _request(self, endpoint: str, payload=None) -> dict[str, object]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise OllamaError("Ollama HTTP hatası {}: {}".format(error.code, detail)) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise OllamaError(
                "Ollama'ya bağlanılamadı ({}). Ollama'nın açık olduğunu denetleyin.".format(
                    self.base_url
                )
            ) from error
        except json.JSONDecodeError as error:
            raise OllamaError("Ollama geçersiz bir HTTP yanıtı döndürdü.") from error
        if not isinstance(result, dict):
            raise OllamaError("Ollama yanıtının biçimi beklenenden farklı.")
        return result

    def installed_models(self) -> list[str]:
        result = self._request("/api/tags")
        models = result.get("models", [])
        return [
            item["name"]
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]

    def check_model(self) -> None:
        names = self.installed_models()
        if self.model not in names:
            raise OllamaError(
                "Ollama modeli yüklü değil: {}. Yüklü modeller: {}".format(
                    self.model, ", ".join(names) if names else "yok"
                )
            )

    def extract_terms(self, text: str) -> list[ExtractedTerm]:
        """Few-shot istemiyle yalnızca teknik terim adayı üretir."""
        user_prompt = USER_TASK.format(text=text)
        return self._extract_prompt(user_prompt, system=SYSTEM_PROMPT)

    def _extract_prompt(
        self,
        user_prompt: str,
        system: str = SYSTEM_PROMPT,
        num_predict: int = 256,
    ) -> list[ExtractedTerm]:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": user_prompt,
            "format": OUTPUT_SCHEMA,
            "stream": False,
            # Düşünme modelleri yapılandırılmış nesneyi bazen ``thinking`` alanına
            # yazıp ``response`` alanını boş bırakır; terim çıkarımı akıl yürütme
            # izi gerektirmez.
            "think": False,
            "options": {"temperature": 0, "num_predict": num_predict},
        }
        last_error: Exception | None = None
        parsed: dict[str, object] | None = None
        for attempt in range(2):
            retry_instruction = (
                "Return one complete JSON object only, with at most 10 terms. "
                "Do not add commentary."
            )
            payload["prompt"] = (
                user_prompt if not attempt else retry_instruction + "\n\n" + user_prompt
            )
            result = self._request("/api/generate", payload)
            response_text = result.get("response")
            if not isinstance(response_text, str):
                last_error = OllamaError("Ollama yanıtında 'response' alanı bulunamadı.")
                continue
            if not response_text.strip():
                last_error = OllamaError(
                    "Model boş yanıt döndürdü. 'think' parametresi kapalıyken "
                    "model çıktıyı 'thinking' alanına yazmış olabilir."
                )
                continue
            try:
                parsed = _json_from_text(response_text)
                break
            except OllamaError as error:
                last_error = error
        if parsed is None:
            raise last_error or OllamaError("Model geçerli JSON döndürmedi.")
        raw_terms = None
        if isinstance(parsed, dict):
            for key in ("terms", "extracted_terms", "technical_terms", "candidates", "keywords"):
                if isinstance(parsed.get(key), list):
                    raw_terms = parsed[key]
                    break
            if raw_terms is None:
                if not parsed or all(v is None or v == [] or v == {} for v in parsed.values()):
                    raw_terms = []
                else:
                    raise OllamaError("Model yanıtında 'terms' listesi bulunamadı.")
        elif isinstance(parsed, list):
            raw_terms = parsed
        else:
            raise OllamaError("Model yanıtı geçerli JSON nesnesi veya listesi değil.")

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
