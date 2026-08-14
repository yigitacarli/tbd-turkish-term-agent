import json
import unittest
from unittest.mock import patch

from terim_etmeni.models import ExtractedTerm
from terim_etmeni_v2.api_client import ApiClient, ApiClientError


def _api_response(terms):
    return {
        "choices": [{"message": {"content": json.dumps({"terms": terms})}}]
    }


class ApiClientTests(unittest.TestCase):
    def setUp(self):
        self.client = ApiClient(
            "https://api.example.com/v1", "model-x", "secret", timeout=5
        )

    def test_extract_parses_terms_from_chat_response(self):
        def fake_open(request, timeout):
            body = request.data.decode("utf-8")
            payload = json.loads(body)
            self.assertIn("chat/completions", request.full_url)
            self.assertEqual(
                request.get_header("Authorization"), "Bearer secret"
            )
            self.assertEqual(payload["model"], "model-x")
            self.assertEqual(payload["temperature"], 0)

            class Response:
                def read(self):
                    return json.dumps(
                        _api_response(["machine learning", "neural network"])
                    ).encode("utf-8")

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            return Response()

        with patch("urllib.request.urlopen", side_effect=fake_open):
            terms = self.client.extract("some text")
        self.assertEqual(
            [term.term for term in terms], ["machine learning", "neural network"]
        )

    def test_validate_terms_keeps_only_exact_candidates(self):
        def fake_open(request, timeout):
            class Response:
                def read(self):
                    return json.dumps(
                        _api_response(["algorithmic recourse"])
                    ).encode("utf-8")

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            return Response()

        with patch("urllib.request.urlopen", side_effect=fake_open):
            accepted = self.client.validate_terms(
                ["algorithmic recourse", "noise phrase"]
            )
        self.assertEqual(accepted, ["algorithmic recourse"])

    def test_empty_choice_raises(self):
        def fake_open(request, timeout):
            class Response:
                def read(self):
                    return json.dumps({"choices": []}).encode("utf-8")

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            return Response()

        with patch("urllib.request.urlopen", side_effect=fake_open):
            with self.assertRaises(ApiClientError):
                self.client.extract("text")

    def test_installed_models_returns_configured_model(self):
        self.assertEqual(self.client.installed_models(), ["model-x"])


if __name__ == "__main__":
    unittest.main()
