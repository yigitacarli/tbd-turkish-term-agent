"""Model adaylarını birleştirme ve kaynak metinle doğrulama."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, OrderedDict
from typing import Protocol

from .dictionary import normalized_key
from .models import ExtractedTerm, PageText, TermEvidence, TextChunk


_MODEL_PRODUCT_PATTERN = re.compile(
    r"\b(?:dall[ -]?e|stable diffusion|glide|nvidia|a100|clip)\b", re.IGNORECASE
)

_TECHNICAL_HEADS = {
    # Core CS / Software
    "algorithm", "architecture", "abstraction", "automation", "analytics",
    "api", "authentication", "authorization",
    # Data & AI
    "cache", "classifier", "clustering", "computation", "compiler",
    "containerization", "controller", "convergence",
    # Databases & Storage
    "database", "datastore", "decoder", "deployment", "detection",
    # ML / Deep Learning
    "diffusion", "distillation", "embedding", "encoder", "encryption",
    "estimation", "extraction",
    # Infrastructure
    "failover", "firewall", "firmware", "framework",
    # Networking
    "gateway", "generation", "graph",
    # Data structures & indexing
    "hashing", "hypervisor",
    "index", "inference", "instrumentation", "integration", "interface",
    "interoperability",
    # AI/ML continued
    "kernel", "learning", "lifecycle", "linearization", "localization",
    # Distributed systems
    "mesh", "microservice", "middleware", "migration", "model",
    "monitoring", "multiplexing",
    # Networking & orchestration
    "network", "normalization",
    "observability", "offloading", "optimization", "orchestration",
    # Data processing
    "parallelism", "parser", "partitioning", "pipeline", "pooling",
    "processor", "profiling", "protocol", "provisioning", "proxy",
    # ML / NLP
    "quantization",
    "recognition", "regression", "regularization", "replication",
    "representation", "resolution", "retrieval", "router", "routing", "runtime",
    # Security & systems
    "sandbox", "scalability", "scheduler", "schema", "security",
    "segmentation", "serialization", "server", "sharding",
    "simulator", "specification", "stack", "storage", "streaming",
    "synchronization",
    # Web & infra
    "telemetry", "tokenization", "topology", "tracing", "transformer",
    "tree", "tunneling",
    # Misc
    "validation", "virtualization", "vulnerability",
    "workflow",
}

_STRONG_TECHNICAL_HEADS = {
    "authentication", "authorization", "blockchain", "containerization",
    "encryption", "firewall", "hypervisor", "inference", "interoperability",
    "microservice", "middleware", "orchestration", "protocol", "quantization",
    "recognition", "router", "schema", "serialization", "sharding",
    "tokenization", "topology", "tree", "virtualization", "vulnerability",
}

_PHRASE_BOUNDARIES = {
    "a", "after", "an", "and", "are", "as", "at", "authors", "based", "be",
    "been", "before", "being", "both", "by", "can", "compared", "describes",
    "discussed", "during", "each", "every", "first", "for", "from", "has",
    "have", "how", "in", "into", "is", "it", "its", "of", "on", "only", "or",
    "our", "over", "previous", "same", "shows", "that", "the", "their", "these",
    "they", "this", "those", "through", "to", "uses", "using", "was", "we",
    "were", "which", "while", "with", "approach", "approaches", "introduced",
    "leveraging", "manage", "manages", "provide", "provides",
}

_GENERIC_LEADING_MODIFIERS = {
    "different", "multiple", "new", "novel", "proposed", "several", "various",
}

_FRAGMENT_LEADING_WORDS = {
    "and", "as", "at", "between", "by", "for", "from", "if", "in", "into",
    "is", "of", "on", "or", "than", "the", "to", "with", "without",
}

_REFERENCE_NOISE_PATTERN = re.compile(
    r"\b(?:proceedings|et al|arxiv|preprint|journal of|conference on)\b",
    re.IGNORECASE,
)


def _is_tabular_line(line: str) -> bool:
    """Sayısal deney tablosu satırlarını, düz metinden ayırır.

    PDF metin katmanı tablo başlıklarını normal bir cümle gibi döndürebilir.
    Tek başına bu başlıklar sözlüğe eklenecek terimler değildir. Eşik yalnızca
    birden çok sayısal hücre içeren satırlar için uygulanır; teknik metindeki
    sürüm veya boyut numaraları bundan etkilenmez.
    """
    return len(re.findall(r"\b\d+(?:\.\d+)?(?:%|[A-Za-z]+)?\b", line)) >= 3


def _is_structured_table_row(line: str) -> bool:
    """Sayı içermeyen değerlendirme-tablosu satırlarını tanır.

    Bazı PDF'ler (özellikle word-analogy değerlendirmeleri) tablo hücrelerini
    yalnızca sözcük çiftleri halinde çıkarır. Bu satırlar cümle değildir ve
    teknik terim için güvenilir kanıt sayılmaz.
    """
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", line)
    if not 4 <= len(tokens) <= 8 or re.search(r"[.!?;:]", line):
        return False
    stop_words = {
        "a", "an", "and", "are", "as", "for", "from", "in", "is", "of",
        "on", "or", "that", "the", "this", "to", "we", "with",
    }
    return not (set(token.casefold() for token in tokens) & stop_words)


def _appears_only_in_tables(term: str, pages: list[PageText]) -> bool:
    pattern = _search_pattern(term)
    matching_contexts: list[tuple[list[str], int]] = []
    for page in pages:
        lines = page.text.splitlines()
        matching_contexts.extend(
            (lines, index) for index, line in enumerate(lines) if pattern.search(line)
        )
    if not matching_contexts:
        return False

    def tabular_or_heading(lines: list[str], index: int) -> bool:
        if _is_tabular_line(lines[index]):
            return True
        # pdfplumber çoğu tabloda sütun başlığını ayrı bir satır olarak verir.
        # Başlıktan sonraki üç satırın ikisi sayısal hücreyse bu da tablo
        # bağlamıdır; düz metinde böyle bir düzen beklenmez.
        following = lines[index + 1 : index + 4]
        if sum(_is_tabular_line(line) for line in following) >= 2:
            return True
        nearby = lines[max(0, index - 2) : index + 3]
        return (
            _is_structured_table_row(lines[index])
            and sum(
                _is_structured_table_row(line) or _is_tabular_line(line)
                for line in nearby
            ) >= 3
        )

    return all(tabular_or_heading(lines, index) for lines, index in matching_contexts)


class TermProvider(Protocol):
    def extract(self, text: str) -> list[ExtractedTerm]:
        ...


def _plausible_term(term: str) -> bool:
    words = term.split()
    if len(term) > 100 or (len(words) > 5 and " and " not in term.casefold()):
        return False
    if "\n" in term or ":" in term:
        return False
    if re.match(r"^\d+(?:\.\d+)?[a-z]", term):
        return False
    if re.match(r"^(?:the|a|an|this|these|those|their|our|its)\s+", term, re.IGNORECASE):
        return False
    # Model çıktıları bazen PDF cümlesinin ortasından kesilmiş parçaları terim
    # diye döndürüyor ("between pre-training", "is Service Provider").
    # Edat veya bağlaçla başlayan bu tür diziler bağımsız teknik ad olamaz.
    if words and words[0].casefold() in _FRAGMENT_LEADING_WORDS:
        return False
    if re.match(r"^i-th\b", term, re.IGNORECASE):
        return False
    # "cybersecurity- or privacy-supporting capability" gibi koordinasyonlu
    # cümle parçaları bağımsız terim değildir. Terim çıkarıcı bunları bölmek
    # yerine zaten ayrı teknik isim öbeklerini yakalamalıdır.
    if re.search(r"\bor\b", term, re.IGNORECASE):
        return False
    # Kod değişkenleri (num_heads, batch_size vb.) ve pseudo-code yapıları
    if "_" in term:
        return False
    # PDF'lerden kopan formül değişkenleri ve kod hücreleri (``i k2 T``,
    # ``head1 head0`` gibi) teknik sözlük terimi değildir.
    formula_tokens = sum(
        bool(re.fullmatch(r"(?:[A-Za-z]|[A-Za-z]\d+)", word)) for word in words
    )
    if len(words) >= 2 and formula_tokens >= 2:
        return False
    if any(
        re.fullmatch(r"(?:head|layer|sand|sor|val|vals|bool|bools)\d*", word, re.IGNORECASE)
        for word in words
    ):
        return False
    if any(character in term for character in ("(", ")", "{", "}", "[", "]", ";", "=", "<", ">", "+", "*", "%", "!", "|")):
        return False
    if re.search(
        r"\b(?:def|return|import|assume|select|count|width|tokens|index|decay|steps|loss|config|schedule|gradient|batch|norm|prevs|imbalances|selector|hist|dyck|same_tok|pair_balance|open_for_close)\b",
        term,
        re.IGNORECASE,
    ):
        return False
    if term.casefold() in {
        "siberian husky", "space shuttle", "rhinoceros beetle", "srhinoceros beetle", "coral reef",
        "dows server", "recurrentneuralnetlanguagemodel"
    }:
        return False
    # PDF tablosundan gelen ``TestFrameAccuracy`` benzeri bitişik başlıklar
    # modelce terim sanılabiliyor. Normal İngilizce terimlerde bu iç CamelCase
    # biçimi yoktur; yerleşik kısa adlar zaten tek başına elenmektedir.
    if re.search(r"[a-z]{2,}[A-Z]", term):
        return False
    if re.match(
        r"^(?:theorem|lemma|corollary|proposition|appendix)\s+\d",
        term,
        re.IGNORECASE,
    ):
        return False
    if len(words) >= 2 and all(word.isupper() for word in words if any(char.isalpha() for char in word)):
        return False
    if any(character in term for character in ("[", "]", "“", "”", "∗", "†")):
        return False
    if any(character in "=|∼∑√≈≤≥αβγθ𝛼𝛽𝛾𝜎𝜆𝜇𝜃𝑝" for character in term):
        return False
    if re.fullmatch(r"[A-Za-z]\s*\(\s*[A-Za-z]\s*\)", term):
        return False
    # Kısa teknik adlar (DNS, TLS, AES-ECB vb.) sözlükte gerçekten eksik
    # olabilir. Bunları burada sessizce elemek yerine işlem hattındaki düşük
    # öncelikli insan/model incelemesine bırakırız.
    if _MODEL_PRODUCT_PATTERN.search(term):
        return False
    if re.search(r"\b(?:fig(?:ure)?|table|equation)\.?\s*\d+\b", term, re.IGNORECASE):
        return False
    if re.match(r"^(?:describe|identify|generate)\b", term, re.IGNORECASE):
        return False
    if re.match(r"^(?:give|make|turn)\b", term, re.IGNORECASE):
        return False
    if re.search(r"[?!]", term) or len(re.findall(r"\.(?:\s|$)", term)):
        return False
    if re.search(r"\b(?:AI|artificial intelligence)\s+in\s+", term, re.IGNORECASE):
        return False
    if re.search(r"\b(?:are|were|was)\b", term, re.IGNORECASE):
        return False
    if re.search(
        r"\b(?:acts?|applies?|combines?|directs?|links?|orders?|performs?|"
        r"produced|receives?|removes?|retains?|selects?|updates?|uses?|used|"
        r"validates?|works?)\b",
        term,
        re.IGNORECASE,
    ):
        return False
    if re.search(
        r"\b(?:abstract|conclusion|discussion|introduction|methodology|overview|"
        r"references|research note|results|sequence)\b$",
        term,
        re.IGNORECASE,
    ):
        return False
    if term.casefold() in {"experimental components"}:
        return False
    return True


def _search_pattern(term: str) -> re.Pattern[str]:
    normalized = unicodedata.normalize("NFKC", term).strip()
    parts = [re.escape(part) for part in re.split(r"[\s\-‐‑‒–—−]+", normalized) if part]
    body = r"[\s\-‐‑‒–—−]+".join(parts)
    if normalized and normalized[0].isalnum():
        body = r"(?<!\w)" + body
    if normalized and normalized[-1].isalnum():
        body += r"(?!\w)"
    return re.compile(body, flags=re.IGNORECASE | re.UNICODE)


def evidence_for(
    term: str,
    pages: list[PageText],
    candidate_sources: set[str] | None = None,
) -> TermEvidence:
    pattern = _search_pattern(term)
    evidence = TermEvidence(term=term, candidate_sources=set(candidate_sources or ()))
    for page in pages:
        count = len(pattern.findall(unicodedata.normalize("NFKC", page.text)))
        if count:
            evidence.pages.add(page.page)
            evidence.occurrence_count += count
    return evidence


def _ngram_candidates(pages: list[PageText]) -> list[tuple[str, str]]:
    """Metindeki 2-gram ve 3-gram İngilizce kelime öbeklerini sistematik olarak tarar.

    Sadece en az bir kelimesinde teknik sinyal (büyük harf kısaltma, bilinen
    teknik sözcük veya tire/rakam içeren bileşik ad) bulunan öbekler alınır.
    Bu fonksiyon spaCy yerine saf regex ile çalışır.
    """
    ngram_recovered: "OrderedDict[str, tuple[str, str]]" = OrderedDict()
    ngram_counts: Counter[str] = Counter()
    word_pattern = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-][A-Za-z0-9]+)*")

    # Teknik sinyal taşıyan kelimeler: büyük harfli kısaltma veya tire/rakam
    # içeren bileşik ad olup olmadığını kontrol eder.
    def _has_technical_signal(word: str) -> bool:
        if word.isupper() and len(word) >= 2:
            return True  # Kısaltma: API, TCP, LLM
        if re.search(r"[0-9]", word):
            return True  # Sürüm/nesil: Wi-Fi, 5G, H.264
        if "-" in word and len(word) >= 4:
            return True  # Bileşik: end-to-end, pre-trained
        if word[0].isupper() and word.casefold() in _TECHNICAL_HEADS:
            return True  # Büyük harfle başlayan teknik terim
        return False

    for page in pages:
        for line in page.text.splitlines():
            if (
                _is_tabular_line(line)
                or _is_structured_table_row(line)
                or _REFERENCE_NOISE_PATTERN.search(line)
            ):
                continue
            words = word_pattern.findall(line)
            # 2-gram ve 3-gram tarama
            for n in (2, 3):
                for i in range(len(words) - n + 1):
                    gram = words[i : i + n]
                    # En az bir kelimede teknik sinyal olmalı
                    if not any(_has_technical_signal(w) for w in gram):
                        continue
                    # Bir bağlaç/edatla başlayıp biten pencereler (``in RASP``,
                    # ``AAAI Conference on``) cümle parçasıdır.
                    if (
                        gram[0].casefold() in _PHRASE_BOUNDARIES
                        or gram[-1].casefold() in _PHRASE_BOUNDARIES
                    ):
                        continue
                    # Koordinasyonun iki yanından kesilmiş n-gramlar (ör.
                    # "or privacy-supporting") teknik terim değil, cümle
                    # parçasıdır.
                    if (
                        any(w.casefold() == "or" for w in gram)
                        or (i > 0 and words[i - 1].casefold() == "or")
                    ):
                        continue
                    # Genel niteleyiciyle başlıyorsa atla
                    if gram[0].casefold() in _GENERIC_LEADING_MODIFIERS:
                        continue
                    term = " ".join(gram)
                    if not _plausible_term(term):
                        continue
                    if any(len(w) > 28 for w in gram):
                        continue
                    key = normalized_key(term)
                    ngram_recovered.setdefault(key, (term, "ngram_scan"))
                    ngram_counts[key] += 1

    # Sadece en az 2 kez geçen n-gramları döndür (gürültüyü azaltmak için)
    return [
        (term, source)
        for key, (term, source) in ngram_recovered.items()
        if ngram_counts[key] >= 2
    ]


def _deterministic_candidates(pages: list[PageText]) -> list[tuple[str, str]]:
    """Modelin atladığı yüksek sinyalli kısa teknik ad öbeklerini geri kazanır.

    İki yöntemle çalışır:
    1. Kontrollü teknik baş sözcüklerden geriye doğru yürüyerek isim öbekleri bulur.
    2. Sistematik N-gram tarayıcısıyla teknik sinyalli 2-3 kelimelik öbekleri toplar.
    Tek başına kısaltmalar ise ancak belgede en az iki kez geçiyorsa eklenir.
    Son karar yine sözlük ve insan/model inceleme aşamalarındadır.
    """
    recovered: "OrderedDict[str, tuple[str, str]]" = OrderedDict()
    phrase_candidates: "OrderedDict[str, str]" = OrderedDict()
    phrase_counts: Counter[str] = Counter()
    acronym_counts: Counter[str] = Counter()
    defined_acronyms: dict[str, str] = {}
    token_pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9]*(?:[-+/][A-Za-z0-9]+)*")
    acronym_pattern = re.compile(
        r"(?<![A-Za-z0-9])(?:[A-Z]{2,10}(?:[-/][A-Z0-9]{1,10})*|[A-Z]{1,4}\d[A-Z0-9-]{1,8}|\d[A-Z][A-Z0-9-]{0,8})(?![A-Za-z0-9])"
    )
    definition_pattern = re.compile(
        r"(?P<long>(?:[A-Za-z][A-Za-z-]*\s+){0,7}[A-Za-z][A-Za-z-]*)\s*"
        r"\((?P<acronym>[A-Z]{2,10})\)"
    )

    def definition_from(match: re.Match[str]) -> tuple[str, str] | None:
        acronym = match.group("acronym")
        words = match.group("long").split()
        # En kısa, sonu paranteze dayanan ve baş harfleri kısaltmayla aynı
        # olan öbeği alırız. Tireli Knowledge-Based -> KB sayılır.
        for start in range(len(words) - 1, -1, -1):
            phrase_words = words[start:]
            initials = "".join(
                part[0]
                for word in phrase_words
                for part in word.split("-")
                if part
            ).upper()
            if initials == acronym:
                return " ".join(phrase_words), acronym
        return None

    for page in pages:
        acronym_counts.update(acronym_pattern.findall(page.text))
        for match in definition_pattern.finditer(page.text):
            definition = definition_from(match)
            if definition:
                long_form, acronym = definition
                defined_acronyms.setdefault(acronym, long_form)
        for line in page.text.splitlines():
            tokens = token_pattern.findall(line)
            for index, token in enumerate(tokens):
                if token.casefold() not in _TECHNICAL_HEADS:
                    continue
                start = index
                while start > 0 and index - start < 3:
                    previous = tokens[start - 1].casefold()
                    if previous in _PHRASE_BOUNDARIES:
                        break
                    start -= 1
                words = tokens[start : index + 1]
                while words and words[0].casefold() in _GENERIC_LEADING_MODIFIERS:
                    words.pop(0)
                if len(words) < 2:
                    continue
                term = " ".join(words)
                if (
                    not any(word.isdigit() or len(word) > 28 for word in words)
                    and not _REFERENCE_NOISE_PATTERN.search(term)
                    and _plausible_term(term)
                ):
                    key = normalized_key(term)
                    phrase_candidates.setdefault(key, term)
                    phrase_counts[key] += 1

    for key, term in phrase_candidates.items():
        head = term.split()[-1].casefold()
        if phrase_counts[key] >= 2 or head in _STRONG_TECHNICAL_HEADS:
            recovered.setdefault(key, (term, "technical_pattern"))

    for long_form in defined_acronyms.values():
        if _plausible_term(long_form):
            recovered.setdefault(
                normalized_key(long_form), (long_form, "defined_term")
            )

    for acronym, count in acronym_counts.items():
        is_generation_name = bool(re.fullmatch(r"\dG", acronym))
        if (acronym in defined_acronyms or (is_generation_name and count >= 2)) and _plausible_term(acronym):
            recovered.setdefault(normalized_key(acronym), (acronym, "repeated_abbreviation"))

    # N-gram tarayıcısı sonuçlarını birleştir (mevcut adayların üzerine yazmaz)
    for term, source in _ngram_candidates(pages):
        recovered.setdefault(normalized_key(term), (term, source))

    return list(recovered.values())


def extract_verified_terms(
    chunks: list[TextChunk],
    pages: list[PageText],
    provider: TermProvider,
    extraction_warnings: list[str] | None = None,
) -> list[TermEvidence]:
    candidates: "OrderedDict[str, str]" = OrderedDict()
    candidate_sources: dict[str, set[str]] = {}

    def add_candidate(term: str, source: str) -> None:
        key = normalized_key(term)
        candidates.setdefault(key, term)
        candidate_sources.setdefault(key, set()).add(source)

    for page in pages:
        for match in re.finditer(r'["“]([^"”]{2,100})["”]', page.text):
            term = " ".join(match.group(1).split()).strip(" \t\r\n,;:")
            if 2 <= len(term.split()) <= 8 and _plausible_term(term):
                add_candidate(term, "quoted_phrase")
    for chunk in chunks:
        prompt = "PAGE {}\n\n{}".format(chunk.page, chunk.text)
        try:
            extracted_terms = provider.extract(prompt)
        except RuntimeError as error:
            if extraction_warnings is None:
                raise
            extraction_warnings.append(
                "Sayfa {} (parça {}): {}".format(chunk.page, chunk.index + 1, error)
            )
            continue
        for extracted in extracted_terms:
            term = " ".join(extracted.term.split()).strip(" \t\r\n,;:")
            if (
                len(term) < 2
                or not any(character.isalpha() for character in term)
                or term.startswith(("http://", "https://"))
                or not _plausible_term(term)
            ):
                continue
            add_candidate(term, "model")

    # Modelin seçtiği yazım biçimi öncelikli kalsın; deterministik tarama yalnız
    # eksik anahtarları ekler ve mevcut adaylara kaynak sinyali iliştirir.
    for term, source in _deterministic_candidates(pages):
        add_candidate(term, source)

    verified = []
    for term in candidates.values():
        evidence = evidence_for(
            term, pages, candidate_sources.get(normalized_key(term), set())
        )
        if evidence.occurrence_count and not _appears_only_in_tables(term, pages):
            verified.append(evidence)
    return verified
