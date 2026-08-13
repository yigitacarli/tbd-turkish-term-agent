"""Ollama HTTP API için küçük ve bağımsız istemci."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Optional

from .models import ExtractedTerm


SYSTEM_PROMPT = """You are a precise English technical-terminology extractor for academic PDFs.
Return only English technical noun phrases that occur verbatim in the supplied text.
Select ONLY high-confidence concepts from computing, software, AI, data,
networking, security, or digital systems. A short accurate list is better than an
exhaustive list. If the supplied text does not contain any eligible technical concepts,
return an empty list. Do not force or invent terms just to return something.

CRITICAL EXCLUSIONS:
- NEVER extract programming code, code variables, hyperparameters, or pseudo-code functions (e.g. num_heads, batch_size, assume_bos, ema_decay).
- NEVER extract dataset class names, image categories, or benchmark labels (e.g. Siberian husky, space shuttle, coral reef).
- NEVER extract long clauses or phrases longer than 5 words.
- Exclude ordinary words; complete clauses; author, person, company, institution, and publication metadata; references and citation keys; conference names; dataset, product, and named model names; figure/table/equation labels; formulas; experiment settings; table column headers and benchmark rows; and image-editing prompts.

Retain established technical abbreviations when they are used as concepts in the text (e.g. machine learning, latent diffusion models, neural network, BERT, RBAC). If an abbreviation and its expansion both occur, return only the expansion.
Do not translate, infer, normalize, or invent terms. Preserve the spelling and number found in the text.
Return only JSON matching the requested schema."""


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
Extract high-confidence noun phrases that name technologies, software
methods, algorithms, systems, or technical components. Include established and
newly coined technical phrases only when they occur exactly in the text.
If no such phrases exist in the text, return an empty list for "terms".
Do not return document titles, section headings, labels, complete sentences,
explanatory prose, names, citations, models, products, datasets, formulas, or
experiment/table fragments.
Prefer specific multi-word phrases, but include a technical single word or
abbreviation when omitting it would lose a distinct concept.
Do not repeat terms from these instructions; only return phrases that occur in
the PDF text between TEXT START and TEXT END.

TEXT START
{text}
TEXT END"""


DISCOVERY_TASK = """INDEPENDENT SECOND REVIEW
Select only additional high-confidence multi-word terminology that the first review
may have missed. Apply every exclusion in the system instructions. Return concise
noun phrases only; do not expand the list with generic, named, or ambiguous items.

TEXT START
{text}
TEXT END"""


TERM_REVIEW_SYSTEM = """You are a conservative technical-terminology reviewer.
From a supplied candidate list, retain only terms that genuinely name a technical
concept, method, algorithm, model component, data representation, mathematical or
statistical concept, or computing system. A candidate can be new or absent from a
dictionary. Reject prose fragments, ordinary contextual descriptions, person names,
benchmark rows, experimental labels, dataset/model names, and generic word groups.
Also reject truncated words, dates and places, organization or team labels, strings
formed by joining adjacent headings or table cells, and phrases that contain two
unrelated concepts accidentally concatenated together. A valid result must be a
self-contained noun phrase that would make sense as one dictionary entry.
When uncertain, reject the candidate. Rejected candidates remain visible to the
human reviewer, while this queue must prioritize precision over list length.
Return only JSON matching the requested schema."""


TERM_REVIEW_TASK = """TECHNICAL TERM REVIEW
Review the exact candidate strings below. Return only the candidates that should
remain in a technical dictionary review queue. Preserve each selected string exactly
as written. Do not add, translate, shorten, normalize, or infer terms.

CANDIDATES
{candidates}
"""


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
    def __init__(
        self, base_url: str, model: str, timeout: int = 240, review_passes: int = 1
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        if review_passes not in (1, 2):
            raise ValueError("İnceleme geçişi sayısı 1 veya 2 olmalı.")
        self.review_passes = review_passes

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
        """Yerel modelle adayların teknik terim niteliğini temkinli doğrular."""
        unique = list(dict.fromkeys(term for term in terms if term.strip()))
        accepted: list[str] = []
        # Çok uzun anketlerde tek istemin bağlamını taşırmamak için küçük gruplar.
        # Küçük yerel modeller uzun karar listelerinde hemen her şeyi kabul
        # etmeye eğilimlidir. Kısa gruplar seçiciliği ve JSON kararlılığını artırır.
        for start in range(0, len(unique), 30):
            batch = unique[start : start + 30]
            prompt = TERM_REVIEW_TASK.format(
                candidates="\n".join("- " + term for term in batch)
            )
            returned = self._extract_prompt(
                prompt,
                system=TERM_REVIEW_SYSTEM,
                num_predict=1024,
                retry_max_terms=None,
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
        num_predict: int = 256,
        retry_max_terms: Optional[int] = 10,
    ) -> list[ExtractedTerm]:
        payload = {
            "model": self.model,
            "system": system,
            "prompt": user_prompt,
            "format": OUTPUT_SCHEMA,
            "stream": False,
            # Qwen 3/3.5 gibi düşünme modelleri yapılandırılmış nesneyi bazen
            # ``thinking`` alanına yazıp ``response`` alanını boş bırakır.
            # Terim çıkarımı akıl yürütme izi gerektirmez; kapatmak hem doğru
            # alanı hem de daha kısa/kararlı yanıtı sağlar.
            "think": False,
            # Kısa terim listesi, daha az ısı ve daha az yarım JSON yanıtı.
            "options": {"temperature": 0, "num_predict": num_predict},
        }
        last_error = None
        parsed = None
        for attempt in range(2):
            retry_instruction = "Return one complete JSON object only. Do not add commentary."
            if retry_max_terms is not None:
                retry_instruction = (
                    "Return one complete JSON object only, with at most {} terms. "
                    "Do not add commentary."
                ).format(retry_max_terms)
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
