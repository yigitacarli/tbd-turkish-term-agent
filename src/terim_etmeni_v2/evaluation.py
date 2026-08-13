"""Uzman etiketli kabul kümesiyle çevrimdışı V1/V2 kalite ölçümü."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from terim_etmeni.dictionary import normalized_key


LABELS = {"dictionary_match", "missing_term", "noise"}
PREDICTED_GROUPS = {
    "dictionary_matches": "dictionary_match",
    "possible_matches": "possible_match",
    "missing_terms": "missing_term",
    "rejected_candidates": "noise",
}


class EvaluationError(ValueError):
    """Kabul kümesi veya sonuç raporu ölçülemiyorsa üretilir."""


@dataclass(frozen=True)
class GoldDocument:
    document: str
    labels: dict[str, str]


def _document_key(value: object) -> str:
    name = Path(str(value or "")).name.casefold()
    if not name:
        raise EvaluationError("Belge adı boş olamaz.")
    return name


def load_acceptance_set(path: Path) -> dict[str, GoldDocument]:
    """Eksiksiz etiketlenmiş kabul kümesini yükler ve doğrular."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvaluationError("Kabul kümesi okunamadı: {}".format(error)) from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise EvaluationError("Kabul kümesi schema_version değeri 1 olmalıdır.")
    if payload.get("review_status") == "internal_draft":
        raise EvaluationError(
            "İç değerlendirme taslağı onaylanmadan ölçümde kullanılamaz."
        )
    documents = payload.get("documents")
    if not isinstance(documents, list) or not documents:
        raise EvaluationError("Kabul kümesinde en az bir belge olmalıdır.")

    loaded: dict[str, GoldDocument] = {}
    for raw_document in documents:
        if not isinstance(raw_document, dict):
            raise EvaluationError("Her kabul kümesi belgesi bir nesne olmalıdır.")
        document = str(raw_document.get("document", "")).strip()
        key = _document_key(document)
        if key in loaded:
            raise EvaluationError("Kabul kümesinde yinelenen belge: {}".format(document))
        raw_terms = raw_document.get("terms")
        if not isinstance(raw_terms, list) or not raw_terms:
            raise EvaluationError("{} için en az bir etiket gerekir.".format(document))
        labels: dict[str, str] = {}
        for raw_term in raw_terms:
            if not isinstance(raw_term, dict):
                raise EvaluationError("{} içinde geçersiz terim etiketi.".format(document))
            term = str(raw_term.get("term", "")).strip()
            label = str(raw_term.get("label", "")).strip()
            normalized = normalized_key(term)
            if not normalized:
                raise EvaluationError("{} içinde boş terim etiketi.".format(document))
            if label not in LABELS:
                raise EvaluationError(
                    "{} etiketi geçersiz; beklenen: {}".format(
                        label or "(boş)", ", ".join(sorted(LABELS))
                    )
                )
            if normalized in labels:
                raise EvaluationError(
                    "{} içinde yinelenen terim: {}".format(document, term)
                )
            labels[normalized] = label
        loaded[key] = GoldDocument(document=document, labels=labels)
    return loaded


def load_result_reports(paths: Iterable[Path]) -> dict[str, dict[str, object]]:
    """Bir sisteme ait JSON raporlarını belge adına göre yükler."""
    payloads: list[tuple[str, bytes]] = []
    for path in paths:
        try:
            payloads.append((str(path), Path(path).read_bytes()))
        except OSError as error:
            raise EvaluationError(
                "Sonuç raporu okunamadı ({}): {}".format(path, error)
            ) from error
    return load_result_payloads(payloads)


def load_result_payloads(
    payloads: Iterable[tuple[str, bytes]],
) -> dict[str, dict[str, object]]:
    """Yüklenen JSON rapor içeriklerini belge adına göre doğrular."""
    reports: dict[str, dict[str, object]] = {}
    for source, content in payloads:
        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EvaluationError(
                "Sonuç raporu okunamadı ({}): {}".format(source, error)
            ) from error
        if not isinstance(payload, dict):
            raise EvaluationError("Sonuç raporu nesne olmalıdır: {}".format(source))
        key = _document_key(payload.get("document"))
        if key in reports:
            raise EvaluationError("Yinelenen sonuç belgesi: {}".format(payload.get("document")))
        reports[key] = payload
    return reports


def _predictions(report: dict[str, object]) -> dict[str, str]:
    predicted: dict[str, str] = {}
    for group, label in PREDICTED_GROUPS.items():
        values = report.get(group, [])
        if not isinstance(values, list):
            raise EvaluationError("{} alanı liste olmalıdır.".format(group))
        for item in values:
            if not isinstance(item, dict):
                continue
            term = normalized_key(str(item.get("term", "")))
            if not term:
                continue
            if term in predicted and predicted[term] != label:
                raise EvaluationError("Aynı terim birden fazla sonuç grubunda: {}".format(term))
            predicted[term] = label
    return predicted


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def evaluate_reports(
    acceptance: dict[str, GoldDocument],
    reports: dict[str, dict[str, object]],
) -> dict[str, object]:
    """Tek bir sistemin raporlarını kabul kümesine göre puanlar."""
    technical_tp = technical_fp = technical_fn = 0
    missing_tp = missing_fp = missing_fn = 0
    noise_correct = noise_total = 0
    labelled_total = exact_correct = 0
    unlabelled_predictions = 0
    durations: list[float] = []
    status_counts: dict[str, int] = {}
    missing_documents: list[str] = []

    for key, gold_document in acceptance.items():
        report = reports.get(key)
        if report is None:
            missing_documents.append(gold_document.document)
            predictions: dict[str, str] = {}
        else:
            predictions = _predictions(report)
            status = str(report.get("analysis_status", "unknown"))
            status_counts[status] = status_counts.get(status, 0) + 1
            duration = report.get("analysis_duration_seconds")
            if isinstance(duration, (int, float)) and duration >= 0:
                durations.append(float(duration))

        gold_technical = {
            term for term, label in gold_document.labels.items() if label != "noise"
        }
        predicted_technical = {
            term for term, label in predictions.items() if label != "noise"
        }
        technical_tp += len(gold_technical & predicted_technical)
        technical_fp += len(predicted_technical - gold_technical)
        technical_fn += len(gold_technical - predicted_technical)

        gold_missing = {
            term for term, label in gold_document.labels.items() if label == "missing_term"
        }
        predicted_missing = {
            term for term, label in predictions.items() if label == "missing_term"
        }
        missing_tp += len(gold_missing & predicted_missing)
        missing_fp += len(predicted_missing - gold_missing)
        missing_fn += len(gold_missing - predicted_missing)

        for term, gold_label in gold_document.labels.items():
            prediction = predictions.get(term, "not_detected")
            labelled_total += 1
            if gold_label == "noise":
                noise_total += 1
                # Gürültünün hiç üretilmemesi de denetim grubuna açıkça
                # alınması kadar doğru davranıştır.
                correctly_suppressed = prediction in {"noise", "not_detected"}
                noise_correct += correctly_suppressed
                exact_correct += correctly_suppressed
            else:
                exact_correct += prediction == gold_label
        unlabelled_predictions += len(set(predictions) - set(gold_document.labels))

    return {
        "documents_expected": len(acceptance),
        "documents_evaluated": len(acceptance) - len(missing_documents),
        "missing_documents": missing_documents,
        "labelled_term_count": labelled_total,
        "unlabelled_prediction_count": unlabelled_predictions,
        "analysis_status_counts": status_counts,
        "duration_seconds": {
            "reported_document_count": len(durations),
            "total": round(sum(durations), 3) if durations else None,
            "average": round(sum(durations) / len(durations), 3) if durations else None,
        },
        "technical_term": {
            "true_positive": technical_tp,
            "false_positive": technical_fp,
            "false_negative": technical_fn,
            "precision": _ratio(technical_tp, technical_tp + technical_fp),
            "recall": _ratio(technical_tp, technical_tp + technical_fn),
        },
        "missing_term": {
            "true_positive": missing_tp,
            "false_positive": missing_fp,
            "false_negative": missing_fn,
            "precision": _ratio(missing_tp, missing_tp + missing_fp),
            "recall": _ratio(missing_tp, missing_tp + missing_fn),
        },
        "noise_rejection_recall": _ratio(noise_correct, noise_total),
        "exact_label_accuracy": _ratio(exact_correct, labelled_total),
    }


def compare_systems(
    acceptance: dict[str, GoldDocument],
    systems: dict[str, dict[str, dict[str, object]]],
) -> dict[str, object]:
    """Aynı kabul kümesinde birden fazla sistemin ölçüm özetini üretir."""
    return {
        "schema_version": 1,
        "acceptance_document_count": len(acceptance),
        "acceptance_term_count": sum(len(item.labels) for item in acceptance.values()),
        "systems": {
            name: evaluate_reports(acceptance, reports)
            for name, reports in systems.items()
        },
    }


def build_acceptance_template(
    systems: dict[str, dict[str, dict[str, object]]]
) -> dict[str, object]:
    """V1/V2 aday birleşiminden insan inceleme şablonu üretir."""
    documents: dict[str, dict[str, object]] = {}
    terms_by_document: dict[str, dict[str, dict[str, object]]] = {}
    for system_name, reports in systems.items():
        for document_key, report in reports.items():
            documents.setdefault(
                document_key, {"document": str(report.get("document", document_key))}
            )
            terms = terms_by_document.setdefault(document_key, {})
            for group in PREDICTED_GROUPS:
                values = report.get(group, [])
                if not isinstance(values, list):
                    raise EvaluationError("{} alanı liste olmalıdır.".format(group))
                for item in values:
                    if not isinstance(item, dict):
                        continue
                    display_term = str(item.get("term", "")).strip()
                    normalized = normalized_key(display_term)
                    if not normalized:
                        continue
                    candidate = terms.setdefault(
                        normalized,
                        {
                            "term": display_term,
                            "label": "",
                            "observed_in": [],
                            "evidence": [],
                        },
                    )
                    observed = candidate["observed_in"]
                    source = "{}:{}".format(system_name, group)
                    if isinstance(observed, list) and source not in observed:
                        observed.append(source)
                    evidence = candidate["evidence"]
                    if isinstance(evidence, list):
                        evidence.append(
                            {
                                "source": source,
                                "pages": item.get("pages", []),
                                "occurrence_count": item.get("occurrence_count", 0),
                            }
                        )

    return {
        "schema_version": 1,
        "documents": [
            {
                "document": documents[key]["document"],
                "terms": sorted(
                    terms_by_document.get(key, {}).values(),
                    key=lambda item: str(item["term"]).casefold(),
                ),
            }
            for key in sorted(documents)
        ],
    }


def format_comparison(result: dict[str, object]) -> str:
    """Karşılaştırmayı terminal için kısa bir tabloya dönüştürür."""
    lines = [
        "Kabul kümesi: {} belge, {} etiket".format(
            result["acceptance_document_count"], result["acceptance_term_count"]
        ),
        "Sistem  Belge  Açık P/R  Teknik P/R  Etiket doğruluğu  Ortalama süre",
    ]
    systems = result.get("systems", {})
    if not isinstance(systems, dict):
        return "\n".join(lines)
    for name, metrics in systems.items():
        if not isinstance(metrics, dict):
            continue
        missing = metrics.get("missing_term", {})
        technical = metrics.get("technical_term", {})
        duration = metrics.get("duration_seconds", {})
        lines.append(
            "{:<7} {}/{}   {}/{}    {}/{}     {}            {}".format(
                name,
                metrics.get("documents_evaluated", 0),
                metrics.get("documents_expected", 0),
                _display_ratio(missing.get("precision") if isinstance(missing, dict) else None),
                _display_ratio(missing.get("recall") if isinstance(missing, dict) else None),
                _display_ratio(technical.get("precision") if isinstance(technical, dict) else None),
                _display_ratio(technical.get("recall") if isinstance(technical, dict) else None),
                _display_ratio(metrics.get("exact_label_accuracy")),
                _display_seconds(duration.get("average") if isinstance(duration, dict) else None),
            )
        )
    return "\n".join(lines)


def _display_ratio(value: object) -> str:
    return "-" if value is None else "{:.1%}".format(float(value))


def _display_seconds(value: object) -> str:
    return "-" if value is None else "{:.2f}s".format(float(value))
