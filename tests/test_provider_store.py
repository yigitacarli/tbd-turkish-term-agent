import tempfile
import unittest
from pathlib import Path

from terim_etmeni.provider_store import ProviderConfig, ProviderConfigStore


class ProviderStoreTests(unittest.TestCase):
    def test_round_trip_and_resolved_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProviderConfigStore(Path(directory) / "provider.json")
            store.save(ProviderConfig("deepseek", "secret-key", "deepseek-chat"))
            config = store.load()
            self.assertEqual(config.provider, "deepseek")
            self.assertEqual(config.api_key, "secret-key")
            self.assertEqual(config.model, "deepseek-chat")

            resolved = store.resolved()
            self.assertEqual(resolved.base_url, "https://api.deepseek.com")

    def test_missing_file_returns_empty_default(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProviderConfigStore(Path(directory) / "none.json")
            config = store.load()
            self.assertEqual(config.provider, "openai")
            self.assertEqual(config.api_key, "")


if __name__ == "__main__":
    unittest.main()
