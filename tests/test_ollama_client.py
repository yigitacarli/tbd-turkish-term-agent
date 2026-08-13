import unittest

from unittest.mock import patch

from terim_etmeni.ollama_client import (
    SYSTEM_PROMPT,
    USER_TASK,
    OllamaClient,
    OllamaError,
    _json_from_text,
)


class OllamaParserTests(unittest.TestCase):
    def test_json_parser_accepts_fenced_json(self):
        result = _json_from_text('```json\n{"terms": []}\n```')
        self.assertEqual(result, {"terms": []})

    def test_json_parser_rejects_invalid_response(self):
        with self.assertRaises(OllamaError):
            _json_from_text("no structured result")

    def test_two_review_passes_are_merged_and_deduplicated(self):
        client = OllamaClient("http://localhost:11434", "fake", review_passes=2)
        responses = [
            {"response": '{"terms":["machine learning","data fabric"]}'},
            {"response": '{"terms":["data fabric","cloud volume"]}'},
        ]
        with patch.object(client, "_request", side_effect=responses):
            terms = client.extract("machine learning, data fabric, and cloud volume")
        self.assertEqual(
            [item.term for item in terms],
            ["machine learning", "data fabric", "cloud volume"],
        )

    def test_default_uses_one_review_pass(self):
        client = OllamaClient("http://localhost:11434", "fake")
        with patch.object(
            client, "_request", return_value={"response": '{"terms":["data fabric"]}'}
        ) as request:
            terms = client.extract("data fabric")
        self.assertEqual([item.term for item in terms], ["data fabric"])
        self.assertEqual(request.call_count, 1)
        self.assertIs(request.call_args.args[1]["think"], False)

    def test_invalid_json_is_retried_with_a_shorter_list_request(self):
        client = OllamaClient("http://localhost:11434", "fake")
        responses = [
            {"response": '{"terms":["unterminated"'},
            {"response": '{"terms":["data fabric"]}'},
        ]
        with patch.object(client, "_request", side_effect=responses) as request:
            terms = client.extract("data fabric")
        self.assertEqual([item.term for item in terms], ["data fabric"])
        self.assertEqual(request.call_count, 2)
        self.assertIn("at most 10 terms", request.call_args_list[1].args[1]["prompt"])

    def test_prompt_allows_an_empty_precise_result_and_keeps_exclusions(self):
        self.assertIn("Select ONLY high-confidence", SYSTEM_PROMPT)
        self.assertIn("return an empty list", SYSTEM_PROMPT)
        self.assertIn("Do not force or invent terms", SYSTEM_PROMPT)
        self.assertIn("dataset,", SYSTEM_PROMPT)
        self.assertIn("table column headers", SYSTEM_PROMPT)
        self.assertIn("established technical abbreviations", SYSTEM_PROMPT)
        self.assertNotIn("at least five", SYSTEM_PROMPT)
        self.assertIn("If no such phrases exist", USER_TASK)
        self.assertIn("experiment/table fragments", USER_TASK)
        self.assertNotIn("formulas, or\nPrefer", USER_TASK)
        self.assertNotIn("Be exhaustive", USER_TASK)

    def test_empty_model_result_is_a_valid_extraction(self):
        client = OllamaClient("http://localhost:11434", "fake")
        with patch.object(client, "_request", return_value={"response": '{"terms":[]}'}) as request:
            terms = client.extract("The authors thank the reviewers.")
        self.assertEqual(terms, [])
        self.assertEqual(request.call_count, 1)

    def test_term_review_keeps_only_exact_returned_candidates(self):
        client = OllamaClient("http://localhost:11434", "fake")
        with patch.object(
            client, "_request", return_value={"response": '{"terms":["data fabric","invented term"]}'}
        ) as request:
            terms = client.validate_terms(["data fabric", "ordinary phrase"])
        self.assertEqual(terms, ["data fabric"])
        payload = request.call_args.args[1]
        self.assertEqual(payload["options"]["num_predict"], 1024)

    def test_term_review_retry_does_not_shorten_the_candidate_list(self):
        client = OllamaClient("http://localhost:11434", "fake")
        responses = [
            {"response": '{"terms":["unterminated"'},
            {"response": '{"terms":["data fabric"]}'},
        ]
        with patch.object(client, "_request", side_effect=responses) as request:
            terms = client.validate_terms(["data fabric", "ordinary phrase"])
        self.assertEqual(terms, ["data fabric"])
        retry_prompt = request.call_args_list[1].args[1]["prompt"]
        self.assertNotIn("at most 10 terms", retry_prompt)


if __name__ == "__main__":
    unittest.main()
