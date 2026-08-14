import unittest

from terim_etmeni.expected_evaluation import evaluate_expected


class ExpectedEvaluationTests(unittest.TestCase):
    def test_counts_detected_missed_and_false_positive_terms(self):
        result = evaluate_expected(
            ["agentic workflow", "tool orchestration"],
            {
                "missing_terms": [
                    {"term": "Agentic Workflow"},
                    {"term": "context window"},
                ]
            },
        )

        self.assertEqual(result["expected_term_count"], 2)
        self.assertEqual(result["correctly_detected"], 1)
        self.assertEqual(result["missed"], 1)
        self.assertEqual(result["false_positives"], 1)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)


if __name__ == "__main__":
    unittest.main()
