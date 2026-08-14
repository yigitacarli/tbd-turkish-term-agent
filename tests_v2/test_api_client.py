import json
import unittest
from unittest.mock import patch

from terim_etmeni_v2.api_client import (
    ApiClient,
    ApiClientError,
    provider_base_url,
    provider_default_model,
)


def _response(body):
    class Response:
        def read(self):
            return json.dumps(body).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    return Response()


class ApiClientTests(unittest.TestCase):
    def test_openai_compatible_request_and_parse(self):
        client = ApiClient("openai", "secret", "model-x", timeout=5)

        def fake_open(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            self.assertIn("chat/completions", request.full_url)
            self.assertEqual(request.get_header("Authorization"), "Bearer secret")
            self.assertEqual(payload["model"], "model-x")
            return _response(
                {"choices": [{"message": {"content": '{"terms": ["neural network"]}'}}]}
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            terms = client.extract("text")
        self.assertEqual([t.term for t in terms], ["neural network"])

    def test_anthropic_request_and_parse(self):
        client = ApiClient("anthropic", "secret", "claude-x", timeout=5)

        def fake_open(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            self.assertIn("/v1/messages", request.full_url)
            self.assertEqual(request.get_header("X-api-key"), "secret")
            self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
            self.assertEqual(payload["messages"][0]["role"], "user")
            return _response(
                {"content": [{"type": "text", "text": '{"terms": ["Paxos"]}'}]}
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            terms = client.extract("text")
        self.assertEqual([t.term for t in terms], ["Paxos"])

    def test_google_request_and_parse(self):
        client = ApiClient("google", "secret", "gemini-x", timeout=5)

        def fake_open(request, timeout):
            self.assertIn("generateContent", request.full_url)
            self.assertIn("key=secret", request.full_url)
            return _response(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": '{"terms": ["chunk"]}'}]}}
                    ]
                }
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            terms = client.extract("text")
        self.assertEqual([t.term for t in terms], ["chunk"])

    def test_provider_defaults(self):
        self.assertEqual(provider_base_url("deepseek"), "https://api.deepseek.com")
        self.assertEqual(provider_default_model("deepseek"), "deepseek-chat")
        self.assertEqual(provider_default_model("google"), "gemini-2.0-flash")
        self.assertEqual(provider_base_url("anthropic"), "https://api.anthropic.com")

    def test_missing_api_key_message_mentions_key(self):
        client = ApiClient("openai", "", "model-x")
        self.assertEqual(client.installed_models(), ["model-x"])

    def test_validate_terms_keeps_exact_candidates(self):
        client = ApiClient("openai", "secret", "model-x", timeout=5)

        def fake_open(request, timeout):
            return _response(
                {"choices": [{"message": {"content": '{"terms": ["read lock"]}'}}]}
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            accepted = client.validate_terms(["read lock", "noise"])
        self.assertEqual(accepted, ["read lock"])


if __name__ == "__main__":
    unittest.main()
