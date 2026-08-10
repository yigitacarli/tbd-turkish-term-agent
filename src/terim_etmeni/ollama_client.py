"""Ollama HTTP API için küçük ve bağımsız istemci."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from .models import ExtractedTerm


SYSTEM_PROMPT = """You extract English information-technology terms from academic text.
Return only terms that occur explicitly in the supplied text.
Include computing, software, artificial intelligence, data, networking, security,
and digital-technology concepts. Preserve multi-word terms as phrases. Exclude
ordinary words, author names, institutions, journal metadata, headings, and
bibliography entries. Do not translate and do not invent or infer terms.
Include newly coined or experimental technical phrases when they occur explicitly;
dictionary membership is decided later by the application, not by you.
Return JSON matching the requested schema. Use the spelling found in the text.
If an abbreviation and its expansion are both explicit, use the expansion as
the term."""


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "terms": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["terms"],
}


USER_TASK = """TASK
Extract noun phrases from the text that name technologies, software methods,
algorithms, systems, or technical components. Include both established terms and
newly coined terms. Be exhaustive and inspect every sentence. Do not return the document title, section headings, labels,
complete sentences, or explanatory prose.
Return the shortest canonical noun phrase, never a clause containing an action verb.

Example text: The service uses machine learning and a semantic signal router.
Example result: {{"terms":["machine learning","semantic signal router"]}}

TEXT START
{text}
TEXT END"""


DISCOVERY_TASK = """INDEPENDENT SECOND REVIEW
Scan the text again for domain-specific multi-word terminology that a first review
might miss. Focus on artificial intelligence, data, cloud, networking, security,
software, automation, and computing phrases. Include plural forms and explicit new
compound terms. Exclude companies, industries, application domains, headings,
ordinary words, and clauses containing verbs. Return concise noun phrases only.

TEXT START
{text}
TEXT END"""


class OllamaError(RuntimeError):
    pass


def _json_from_text(raw: str) -> dict[str, object]:
    value = raw.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise OllamaError("Model geçerli JSON döndürmedi.")
        try:
            parsed = json.loads(value[start : end + 1])
        except json.JSONDecodeError as error:
            raise OllamaError("Model geçerli JSON döndürmedi.") from error
    if not isinstance(parsed, dict):
        raise OllamaError("Model yanıtı bir JSON nesnesi değil.")
    return parsed


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

    def extract(self, text: str) -> list[ExtractedTerm]:
        output: list[ExtractedTerm] = []
        seen = set()
        for template in (USER_TASK, DISCOVERY_TASK):
            user_prompt = template.format(text=text)
            for extracted in self._extract_prompt(user_prompt):
                key = extracted.term.casefold()
                if key not in seen:
                    seen.add(key)
                    output.append(extracted)
        return output

    def _extract_prompt(self, user_prompt: str) -> list[ExtractedTerm]:
        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "prompt": user_prompt,
            "format": OUTPUT_SCHEMA,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 768},
        }
        last_error = None
        parsed = None
        for attempt in range(2):
            payload["prompt"] = (
                user_prompt
                if not attempt
                else "Return one complete JSON object only. Do not add commentary.\n\n"
                + user_prompt
            )
            result = self._request("/api/generate", payload)
            response_text = result.get("response")
            if not isinstance(response_text, str):
                last_error = OllamaError("Ollama yanıtında 'response' alanı bulunamadı.")
                continue
            try:
                parsed = _json_from_text(response_text)
                break
            except OllamaError as error:
                last_error = error
        if parsed is None:
            raise last_error or OllamaError("Model geçerli JSON döndürmedi.")
        raw_terms = parsed.get("terms")
        if not isinstance(raw_terms, list):
            raise OllamaError("Model yanıtında 'terms' listesi bulunamadı.")

        output: list[ExtractedTerm] = []
        for item in raw_terms:
            if isinstance(item, str):
                term, variants = item.strip(), ()
            elif isinstance(item, dict):
                value = item.get("term")
                term = value.strip() if isinstance(value, str) else ""
                raw_variants = item.get("variants", [])
                variants = tuple(
                    value.strip()
                    for value in raw_variants
                    if isinstance(value, str) and value.strip()
                ) if isinstance(raw_variants, list) else ()
            else:
                continue
            if term:
                output.append(ExtractedTerm(term=term, variants=variants))
        return output
