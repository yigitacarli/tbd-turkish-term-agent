import json
import unittest
import urllib.error
from unittest.mock import patch

from terim_etmeni.api_client import (
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
            self.assertEqual(payload["response_format"], {"type": "json_object"})
            return _response(
                {"choices": [{"message": {"content": '{"terms": ["neural network"]}'}}]}
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            terms = client.extract_terms("text")
        self.assertEqual([t.term for t in terms], ["neural network"])

    def test_deepseek_uses_json_mode_and_disables_thinking(self):
        client = ApiClient("deepseek", "secret", "deepseek-v4-flash", timeout=5)

        def fake_open(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            self.assertEqual(payload["response_format"], {"type": "json_object"})
            self.assertEqual(payload["thinking"], {"type": "disabled"})
            self.assertEqual(payload["max_tokens"], 4096)
            return _response(
                {"choices": [{"message": {"content": '{"terms": []}'}}]}
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            self.assertEqual(client.extract_terms("text"), [])

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
            terms = client.extract_terms("text")
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
            terms = client.extract_terms("text")
        self.assertEqual([t.term for t in terms], ["chunk"])

    def test_object_terms_are_parsed(self):
        client = ApiClient("openai", "secret", "model-x", timeout=5)

        def fake_open(request, timeout):
            return _response(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"terms": [{"term": "context window", "context": "..."}]}'
                            }
                        }
                    ]
                }
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            terms = client.extract_terms("text")
        self.assertEqual([t.term for t in terms], ["context window"])

    def test_provider_defaults(self):
        self.assertEqual(provider_base_url("deepseek"), "https://api.deepseek.com")
        self.assertEqual(provider_default_model("deepseek"), "deepseek-v4-flash")
        self.assertEqual(provider_default_model("google"), "gemini-2.0-flash")
        self.assertEqual(provider_base_url("anthropic"), "https://api.anthropic.com")

    def test_missing_api_key_message_mentions_key(self):
        client = ApiClient("openai", "", "model-x")
        self.assertEqual(client.installed_models(), ["model-x"])

    def test_openai_o1_model_uses_max_completion_tokens(self):
        client = ApiClient("openai", "secret", "o1-mini", timeout=5)

        def fake_open(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            self.assertEqual(payload["max_completion_tokens"], 4096)
            self.assertNotIn("temperature", payload)
            self.assertNotIn("response_format", payload)
            return _response(
                {"choices": [{"message": {"content": '{"terms": ["chain of thought"]}'}}]}
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            terms = client.extract_terms("text")
        self.assertEqual([t.term for t in terms], ["chain of thought"])

    def test_deepseek_reasoner_omits_thinking_and_json_mode(self):
        client = ApiClient("deepseek", "secret", "deepseek-reasoner", timeout=5)

        def fake_open(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            self.assertNotIn("thinking", payload)
            self.assertNotIn("response_format", payload)
            return _response(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "reasoning_content": '{"terms": ["consensus"]}',
                            }
                        }
                    ]
                }
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            terms = client.extract_terms("text")
        self.assertEqual([t.term for t in terms], ["consensus"])

    def test_google_prompt_feedback_block_reason(self):
        client = ApiClient("google", "secret", "gemini-2.5-flash", timeout=5)

        def fake_open(request, timeout):
            return _response(
                {
                    "candidates": [],
                    "promptFeedback": {"blockReason": "SAFETY"},
                }
            )

        with patch("urllib.request.urlopen", side_effect=fake_open):
            with self.assertRaises(ApiClientError) as ctx:
                client.extract_terms("text")
            self.assertIn("SAFETY", str(ctx.exception))

    def test_model_name_spaces_are_normalized(self):
        client = ApiClient("google", "secret", "gemini 2.5 flash")
        self.assertEqual(client.model, "gemini-2.5-flash")

    def test_rate_limit_429_retries_and_succeeds(self):
        import io
        import urllib.error
        client = ApiClient("google", "secret", "gemini-2.5-flash", timeout=5)
        attempts = 0

        def fake_open(request, timeout):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                fp = io.BytesIO(b'{"error": {"code": 429, "message": "Resource exhausted. retry in 0.1s"}}')
                raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, fp)
            return _response(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": '{"terms": ["smart contract"]}'}]}}
                    ]
                }
            )

        with patch("urllib.request.urlopen", side_effect=fake_open), patch("time.sleep") as mock_sleep:
            terms = client.extract_terms("text")
        self.assertEqual([t.term for t in terms], ["smart contract"])
        self.assertEqual(attempts, 2)
        mock_sleep.assert_called()

    def test_empty_dict_and_alternative_keys_are_recovered(self):
        client = ApiClient("openai", "secret", "model-x", timeout=5)

        with patch("urllib.request.urlopen", return_value=_response(
            {"choices": [{"message": {"content": "{}"}}]}
        )):
            self.assertEqual(client.extract_terms("text"), [])

        with patch("urllib.request.urlopen", return_value=_response(
            {"choices": [{"message": {"content": '{"technical_terms": [{"term": "hash function"}]}'}}]}
        )):
            terms = client.extract_terms("text")
            self.assertEqual([t.term for t in terms], ["hash function"])

    def test_quota_exceeded_fails_fast_with_clear_message(self):
        client = ApiClient("google", "secret", "gemini-2.5-flash", timeout=5)

        def fake_open(request, timeout):
            import io
            fp = io.BytesIO(b'{"error": {"code": 429, "message": "You exceeded your current quota, please check your plan"}}')
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, fp)

        with patch("urllib.request.urlopen", side_effect=fake_open), self.assertRaisesRegex(
            ApiClientError, "kullanım kotanız doldu"
        ):
            client.extract_terms("text")


if __name__ == "__main__":
    unittest.main()


