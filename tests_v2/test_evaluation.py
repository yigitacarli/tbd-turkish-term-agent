import json
import tempfile
import unittest
from pathlib import Path

from terim_etmeni_v2.cli import main
from terim_etmeni_v2.evaluation import (
    EvaluationError,
    build_acceptance_template,
    compare_systems,
    load_acceptance_set,
    load_result_payloads,
    load_result_reports,
)


class EvaluationTests(unittest.TestCase):
    def _write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_reports_are_compared_with_precision_recall_and_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            acceptance_path = self._write(
                root / "acceptance.json",
                {
                    "schema_version": 1,
                    "documents": [
                        {
                            "document": "article.pdf",
                            "terms": [
                                {"term": "machine learning", "label": "dictionary_match"},
                                {"term": "new protocol", "label": "missing_term"},
                                {"term": "John Example", "label": "noise"},
                            ],
                        }
                    ],
                },
            )
            v1_path = self._write(
                root / "v1.json",
                {
                    "document": "article.pdf",
                    "analysis_status": "complete",
                    "dictionary_matches": [{"term": "machine learning"}],
                    "possible_matches": [],
                    "missing_terms": [
                        {"term": "new protocol"},
                        {"term": "ordinary phrase"},
                    ],
                    "rejected_candidates": [{"term": "John Example"}],
                    "analysis_duration_seconds": 12.5,
                },
            )
            acceptance = load_acceptance_set(acceptance_path)
            reports = load_result_reports([v1_path])
            result = compare_systems(acceptance, {"v1": reports})

        metrics = result["systems"]["v1"]
        self.assertEqual(metrics["missing_term"]["recall"], 1.0)
        self.assertEqual(metrics["missing_term"]["precision"], 0.5)
        self.assertEqual(metrics["technical_term"]["recall"], 1.0)
        self.assertEqual(metrics["unlabelled_prediction_count"], 1)
        self.assertEqual(metrics["exact_label_accuracy"], 1.0)
        self.assertEqual(metrics["duration_seconds"]["average"], 12.5)

    def test_missing_report_counts_as_missed_gold_terms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            acceptance_path = self._write(
                root / "acceptance.json",
                {
                    "schema_version": 1,
                    "documents": [
                        {
                            "document": "missing.pdf",
                            "terms": [{"term": "new protocol", "label": "missing_term"}],
                        }
                    ],
                },
            )
            result = compare_systems(load_acceptance_set(acceptance_path), {"v2": {}})
        metrics = result["systems"]["v2"]
        self.assertEqual(metrics["documents_evaluated"], 0)
        self.assertEqual(metrics["missing_term"]["false_negative"], 1)

    def test_noise_not_generated_by_a_system_is_correctly_suppressed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            acceptance_path = self._write(
                root / "acceptance.json",
                {
                    "schema_version": 1,
                    "documents": [
                        {
                            "document": "article.pdf",
                            "terms": [{"term": "John Example", "label": "noise"}],
                        }
                    ],
                },
            )
            report_path = self._write(
                root / "result.json",
                {
                    "document": "article.pdf",
                    "dictionary_matches": [],
                    "possible_matches": [],
                    "missing_terms": [],
                    "rejected_candidates": [],
                },
            )
            result = compare_systems(
                load_acceptance_set(acceptance_path),
                {"v2": load_result_reports([report_path])},
            )
        metrics = result["systems"]["v2"]
        self.assertEqual(metrics["noise_rejection_recall"], 1.0)
        self.assertEqual(metrics["exact_label_accuracy"], 1.0)

    def test_unknown_label_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                Path(directory) / "acceptance.json",
                {
                    "schema_version": 1,
                    "documents": [
                        {
                            "document": "article.pdf",
                            "terms": [{"term": "term", "label": "maybe"}],
                        }
                    ],
                },
            )
            with self.assertRaises(EvaluationError):
                load_acceptance_set(path)

    def test_internal_draft_cannot_be_used_as_final_measurement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write(
                Path(directory) / "acceptance.json",
                {
                    "schema_version": 1,
                    "review_status": "internal_draft",
                    "documents": [
                        {
                            "document": "article.pdf",
                            "terms": [
                                {"term": "machine learning", "label": "dictionary_match"}
                            ],
                        }
                    ],
                },
            )
            with self.assertRaisesRegex(EvaluationError, "onaylanmadan"):
                load_acceptance_set(path)

    def test_acceptance_template_uses_union_and_shows_each_source_group(self):
        v1 = {
            "article.pdf": {
                "document": "article.pdf",
                "dictionary_matches": [{"term": "Machine Learning"}],
                "possible_matches": [],
                "missing_terms": [{"term": "New Protocol"}],
                "rejected_candidates": [],
            }
        }
        v2 = {
            "article.pdf": {
                "document": "article.pdf",
                "dictionary_matches": [{"term": "machine learning"}],
                "possible_matches": [],
                "missing_terms": [],
                "rejected_candidates": [{"term": "New Protocol"}],
            }
        }
        template = build_acceptance_template({"v1": v1, "v2": v2})
        terms = {item["term"].casefold(): item for item in template["documents"][0]["terms"]}
        self.assertEqual(len(terms), 2)
        self.assertEqual(terms["machine learning"]["label"], "")
        self.assertEqual(
            terms["new protocol"]["observed_in"],
            ["v1:missing_terms", "v2:rejected_candidates"],
        )
        self.assertEqual(
            [item["source"] for item in terms["new protocol"]["evidence"]],
            ["v1:missing_terms", "v2:rejected_candidates"],
        )

    def test_uploaded_result_payloads_are_loaded_without_temporary_files(self):
        report = {
            "document": "article.pdf",
            "dictionary_matches": [],
            "possible_matches": [],
            "missing_terms": [],
            "rejected_candidates": [],
        }
        loaded = load_result_payloads(
            [("article_terms.json", json.dumps(report).encode("utf-8"))]
        )
        self.assertIn("article.pdf", loaded)

    def test_prepare_cli_can_start_from_v2_reports_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report_path = self._write(
                root / "result.json",
                {
                    "document": "article.pdf",
                    "dictionary_matches": [{"term": "machine learning", "pages": [1]}],
                    "possible_matches": [],
                    "missing_terms": [],
                    "rejected_candidates": [],
                },
            )
            output_path = root / "acceptance.json"
            code = main(
                [
                    "prepare-acceptance",
                    "--v2-result",
                    str(report_path),
                    "--output",
                    str(output_path),
                ]
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(payload["documents"][0]["document"], "article.pdf")


if __name__ == "__main__":
    unittest.main()
