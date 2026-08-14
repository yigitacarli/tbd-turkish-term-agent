"""Basit, makale bazlı beklenen eksik-terim ölçümü.

Kullanıcının isteğiyle ana uygulamadan bağımsız hafif bir değerlendirme yapısı:

    evaluation/
        article_01.pdf
        article_01_expected.json

Beklenen dosya biçimi:

    {"expected_missing_terms": ["agentic workflow", "tool orchestration"]}

Ölçüm, bir analiz raporunun ``missing_terms`` grubunu beklenen terimlerle
karşılaştırarak hassasiyet, yakalama, kaçırma ve yanlış pozitif sayısını üretir.
"""
from __future__ import annotations

import json
from pathlib import Path

from .term_extraction import normalize_term


class ExpectedEvaluationError(ValueError):
    pass


def load_expected(path: Path) -> list[str]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExpectedEvaluationError("Beklenen dosya okunamadı: {}".format(error)) from error
    if not isinstance(payload, dict):
        raise ExpectedEvaluationError("Beklenen dosya bir JSON nesnesi olmalıdır.")
    terms = payload.get("expected_missing_terms")
    if not isinstance(terms, list):
        raise ExpectedEvaluationError("expected_missing_terms listesi gerekir.")
    return [str(term).strip() for term in terms if str(term).strip()]


def _report_missing_terms(report: dict) -> set[str]:
    values = report.get("missing_terms", [])
    if not isinstance(values, list):
        raise ExpectedEvaluationError("missing_terms alanı liste olmalıdır.")
    return {
        normalize_term(str(item.get("term", "")))
        for item in values
        if isinstance(item, dict) and str(item.get("term", "")).strip()
    }


def evaluate_expected(expected: list[str], report: dict) -> dict:
    expected_norm = {normalize_term(term) for term in expected}
    detected_norm = _report_missing_terms(report)

    correctly_detected = expected_norm & detected_norm
    missed = expected_norm - detected_norm
    false_positives = detected_norm - expected_norm

    def _ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 4) if denominator else None

    return {
        "expected_term_count": len(expected_norm),
        "correctly_detected": len(correctly_detected),
        "missed": len(missed),
        "false_positives": len(false_positives),
        "precision": _ratio(len(correctly_detected), len(detected_norm)),
        "recall": _ratio(len(correctly_detected), len(expected_norm)),
    }


def format_expected(result: dict) -> str:
    precision = result.get("precision")
    recall = result.get("recall")
    return (
        "Beklenen eksik terim: {expected}\n"
        "Doğru bulunan: {detected}\n"
        "Kaçırılan: {missed}\n"
        "Yanlış pozitif: {fp}\n"
        "Hassasiyet: {precision}\n"
        "Yakalama: {recall}"
    ).format(
        expected=result["expected_term_count"],
        detected=result["correctly_detected"],
        missed=result["missed"],
        fp=result["false_positives"],
        precision="-" if precision is None else "{:.1%}".format(float(precision)),
        recall="-" if recall is None else "{:.1%}".format(float(recall)),
    )
