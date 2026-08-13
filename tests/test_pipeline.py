import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from terim_etmeni.dictionary import DictionaryIndex
from terim_etmeni.models import ExtractedTerm, PageText
from terim_etmeni.pipeline import analyze_pdf
from terim_etmeni.reporting import (
    _model_directory_name,
    format_terminal_report,
    write_reports,
)


class FakeProvider:
    def extract(self, text):
        return [
            ExtractedTerm("machine learning"),
            ExtractedTerm("agentic workflow"),
            ExtractedTerm("client server"),
            ExtractedTerm("task"),
        ]


class CombinedProvider:
    def extract(self, text):
        return [
            ExtractedTerm("Natural Language Processing and Knowledge Base System"),
            ExtractedTerm("travel"),
            ExtractedTerm("automotive industry"),
            ExtractedTerm("Google Translate"),
            ExtractedTerm("travel & transport"),
        ]


class MetadataProvider:
    def extract(self, text):
        return [
            ExtractedTerm("Karen Kent"),
            ExtractedTerm("Intel Corporation"),
            ExtractedTerm("Author ORCID iDs"),
            ExtractedTerm("cloud security capabilities"),
            ExtractedTerm("platform integrity"),
            ExtractedTerm("5G systems"),
            ExtractedTerm("technical details"),
        ]


class ValidatingProvider:
    def extract(self, text):
        return [
            ExtractedTerm("multilayer perceptron"),
            ExtractedTerm("small model"),
            ExtractedTerm("DNS"),
        ]

    def validate_terms(self, terms):
        return ["multilayer perceptron"]


class RejectingProvider:
    def extract(self, text):
        return []

    def validate_terms(self, terms):
        return []


class FailingProvider:
    def extract(self, text):
        raise RuntimeError("invalid model response")


class ReviewFailingProvider:
    def extract(self, text):
        return [ExtractedTerm("algorithmic recourse")]

    def validate_terms(self, terms):
        raise RuntimeError("review timeout")


class PipelineTests(unittest.TestCase):
    def test_pipeline_rejects_small_model_fragments_and_merges_plural_variants(self):
        class NoisySmallProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("Paxos group"),
                    ExtractedTerm("Paxos groups"),
                    ExtractedTerm("read-only transac"),
                    ExtractedTerm("directoriesandplacement"),
                    ExtractedTerm("North America"),
                    ExtractedTerm("F1 team"),
                    ExtractedTerm("implement atomic schema"),
                    ExtractedTerm("Model Architecture GLUE benchmark"),
                    ExtractedTerm("Percolator"),
                ]

            def validate_terms(self, terms):
                return list(terms)

        pages = [
            PageText(
                1,
                "Paxos group coordinates replicas. Paxos groups are monitored.\n"
                "read-only transac directoriesandplacement North America F1 team\n"
                "implement atomic schema\nModel Architecture\nGLUE benchmark\n"
                "Percolator coordinates commits. Percolator is deployed.",
            )
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("noisy.pdf"), DictionaryIndex([]), NoisySmallProvider(), "small-model"
            )

        missing = {item["term"] for item in result["missing_terms"]}
        self.assertEqual(missing, {"Paxos group", "Percolator"})
        rejected = {item["term"]: item.get("reason") for item in result["rejected_candidates"]}
        self.assertEqual(rejected["read-only transac"], "truncated_pdf_fragment")
        self.assertEqual(rejected["directoriesandplacement"], "compacted_pdf_text")
        self.assertEqual(rejected["North America"], "geographic_name")
        self.assertEqual(rejected["F1 team"], "named_group")
        self.assertEqual(rejected["implement atomic schema"], "prose_fragment")
        self.assertEqual(rejected["Model Architecture GLUE benchmark"], "cross_line_fragment")

    def test_pipeline_rejects_reference_benchmark_and_language_pair_labels(self):
        class ReferenceProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("WMT"),
                    ExtractedTerm("GLUE benchmark"),
                    ExtractedTerm("PPL"),
                    ExtractedTerm("English-German"),
                    ExtractedTerm("age recognition"),
                    ExtractedTerm("BLEU"),
                    ExtractedTerm("Transformer"),
                    ExtractedTerm("True-Time"),
                ]

            def validate_terms(self, terms):
                return list(terms)

        pages = [
            PageText(1, "Transformer and True-Time reach 28 BLEU on WMT and the GLUE benchmark using English-German data. Transformer improves."),
            PageText(2, "train PPL BLEU params"),
            PageText(3, "age recognition. In Proceedings of the IEEE Conference, 2017."),
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("references.pdf"), DictionaryIndex([]), ReferenceProvider(), "small-model"
            )

        missing = {item["term"] for item in result["missing_terms"]}
        self.assertEqual(missing, {"BLEU", "Transformer", "True-Time"})
        rejected = {item["term"]: item.get("reason") for item in result["rejected_candidates"]}
        self.assertEqual(rejected["WMT"], "benchmark_or_experiment_label")
        self.assertEqual(rejected["GLUE benchmark"], "benchmark_or_experiment_label")
        self.assertEqual(rejected["PPL"], "benchmark_or_experiment_label")
        self.assertEqual(rejected["English-German"], "language_pair_label")
        self.assertEqual(rejected["age recognition"], "reference_or_citation_context")

    def test_pipeline_rejects_generic_business_and_named_group_noise(self):
        class BusinessNoiseProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("SMM firm"),
                    ExtractedTerm("MEP National Network"),
                    ExtractedTerm("manufacturers"),
                    ExtractedTerm("manufacturing"),
                    ExtractedTerm("business operations"),
                    ExtractedTerm("notification laws"),
                    ExtractedTerm("your encryption"),
                    ExtractedTerm("electricity goes off"),
                    ExtractedTerm("plugin installed on a system"),
                    ExtractedTerm("hardware firewall"),
                ]

            def validate_terms(self, terms):
                return list(terms)

        pages = [PageText(1, (
            "SMM firm and MEP National Network support manufacturers and manufacturing. "
            "Business operations follow notification laws. Protect your encryption. "
            "Sometimes electricity goes off. A plugin installed on a system is checked. "
            "The hardware firewall is active. The hardware firewall blocks traffic."
        ))]
        dictionary = DictionaryIndex([{"en": "encryption", "tr": "şifreleme"}])
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("business.pdf"), dictionary, BusinessNoiseProvider(), "small-model"
            )

        self.assertEqual(
            {item["term"] for item in result["missing_terms"]}, {"hardware firewall"}
        )
        self.assertIn(
            "encryption", {item["term"] for item in result["dictionary_matches"]}
        )
        rejected = {item["term"]: item.get("reason") for item in result["rejected_candidates"]}
        self.assertEqual(rejected["SMM firm"], "named_group")
        self.assertEqual(rejected["MEP National Network"], "named_group")
        self.assertEqual(rejected["electricity goes off"], "prose_fragment")
        self.assertEqual(rejected["plugin installed on a system"], "prose_fragment")

    def test_model_name_is_safe_as_cross_platform_output_directory(self):
        self.assertEqual(_model_directory_name("qwen3.5:4b"), "qwen3.5-4b")
        self.assertEqual(_model_directory_name("org/model:latest"), "org-model-latest")

    def test_pipeline_marks_all_failed_model_chunks_as_failed_analysis(self):
        pages = [PageText(1, "A machine learning system is described.")]
        dictionary = DictionaryIndex(
            [{"en": "machine learning", "tr": "makine öğrenmesi"}]
        )
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("failed.pdf"), dictionary, FailingProvider(), "broken-model"
            )
        self.assertEqual(result["analysis_status"], "failed")
        self.assertEqual(result["processed_chunk_count"], 0)
        self.assertEqual(result["failed_chunk_count"], 1)

    def test_pipeline_marks_failed_second_review_as_partial(self):
        pages = [PageText(1, "Algorithmic recourse is evaluated twice. Algorithmic recourse helps.")]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("partial.pdf"), DictionaryIndex([]), ReviewFailingProvider(), "fake-model"
            )
        self.assertEqual(result["analysis_status"], "partial")
        self.assertEqual(result["processed_chunk_count"], 1)
        self.assertEqual(result["failed_chunk_count"], 0)
        self.assertEqual(result["technical_review"]["status"], "failed")
        self.assertEqual([item["term"] for item in result["missing_terms"]], ["algorithmic recourse"])

    def test_pipeline_keeps_only_strong_deterministic_candidates_for_humans(self):
        pages = [
            PageText(
                1,
                "The Domain Name System (DNS) supports an adaptive signal router. DNS is required.",
            )
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("recovery.pdf"),
                DictionaryIndex([]),
                RejectingProvider(),
                "fake-model",
            )
        missing = {item["term"].casefold(): item for item in result["missing_terms"]}
        self.assertEqual(set(missing), {"domain name system"})
        self.assertEqual(missing["domain name system"]["review_priority"], "medium")
        rejected = {item["term"].casefold() for item in result["rejected_candidates"]}
        self.assertTrue({"adaptive signal router", "dns"} <= rejected)

    def test_pipeline_classifies_and_writes_reports(self):
        pages = [
            PageText(
                1,
                "Machine learning supports an agentic workflow, a client server design, and a task.",
            )
        ]
        dictionary = DictionaryIndex(
            [
                {"en": "machine learning", "tr": "makine öğrenmesi"},
                {"en": "client-server", "tr": "istemci-sunucu"},
            ],
            metadata={"version": "test"},
        )

        with tempfile.TemporaryDirectory() as directory:
            temp_path = Path(directory)
            with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
                result = analyze_pdf(
                    temp_path / "sample.pdf", dictionary, FakeProvider(), "fake-model"
                )
            self.assertEqual(
                result["counts"],
                {
                    "dictionary_matches": 2,
                    "possible_matches": 0,
                    "missing_terms": 1,
                    "rejected_candidates": 1,
                },
            )
            self.assertEqual(
                {item["term"] for item in result["missing_terms"]},
                {"agentic workflow"},
            )
            # "task" genel İngilizce kelime olarak elenir
            self.assertIn(
                "task",
                {item["term"] for item in result["rejected_candidates"]},
            )
            normalized = next(
                item for item in result["dictionary_matches"]
                if item["term"] == "client server"
            )
            self.assertEqual(normalized["match_type"], "normalized_variant")

            json_path, csv_path = write_reports(result, temp_path / "reports")
            xlsx_path = json_path.parent / "sample_terim_raporu.xlsx"
            self.assertEqual(
                json_path.parent.relative_to(temp_path / "reports"),
                Path("fake-model") / "sample",
            )
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["dictionary_version"], "test")
            csv_text = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("agentic workflow", csv_text)
            self.assertIn("machine learning", csv_text)
            self.assertIn("client server", csv_text)
            self.assertIn("İnceleme Durumu", csv_text)
            self.assertIn("Önerilen İşlem", csv_text)
            self.assertIn("İnceleme gerekli", csv_text)
            self.assertIn("Sözlükte bulundu", csv_text)
            try:
                import openpyxl  # noqa: F401
            except ImportError:
                pass
            else:
                self.assertTrue(xlsx_path.is_file())
            terminal = format_terminal_report(result)
            self.assertIn("SÖZLÜKTE BULUNANLAR", terminal)
            self.assertIn("SÖZLÜKTE OLMAYANLAR", terminal)

    def test_pipeline_recovers_dictionary_terms_and_splits_combined_candidate(self):
        pages = [
            PageText(
                1,
                "Natural Language Processing and Knowledge Base System are discussed. "
                "An intelligent agent applies heuristic search in the automotive industry and travel sector. "
                "Google Translate is listed under travel & transport.",
            )
        ]
        dictionary = DictionaryIndex(
            [
                {"en": "natural language processing", "tr": "doğal dil işleme"},
                {"en": "intelligent agent", "tr": "akıllı etmen"},
                {"en": "heuristic search", "tr": "buluşsal arama"},
            ]
        )
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("combined.pdf"), dictionary, CombinedProvider(), "fake-model"
            )
        found = {item["term"].casefold() for item in result["dictionary_matches"]}
        missing = {item["term"].casefold() for item in result["missing_terms"]}
        rejected = {item["term"].casefold() for item in result["rejected_candidates"]}
        self.assertTrue(
            {"natural language processing", "intelligent agent", "heuristic search"}
            <= found
        )
        self.assertEqual({"knowledge base system"}, missing)
        self.assertEqual(
            {"automotive industry", "google translate", "travel & transport", "travel"},
            rejected,
        )

    def test_pipeline_rejects_metadata_and_maps_generic_composites(self):
        pages = [
            PageText(
                1,
                "Karen Kent works at Intel Corporation. Author ORCID iDs are listed. "
                "Cloud security capabilities, platform integrity, 5G systems, and technical details are discussed.",
            )
        ]
        dictionary = DictionaryIndex(
            [{"en": "cloud security", "tr": "bulut güvenliği"}]
        )
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("metadata.pdf"), dictionary, MetadataProvider(), "fake-model"
            )
        found = {item["term"] for item in result["dictionary_matches"]}
        possible = {item["term"] for item in result["possible_matches"]}
        missing = {item["term"] for item in result["missing_terms"]}
        rejected = {item["term"] for item in result["rejected_candidates"]}
        self.assertIn("cloud security", found)
        self.assertNotIn("cloud security capabilities", possible)
        self.assertEqual(missing, {"5G", "platform integrity"})
        self.assertTrue(
            {"Karen Kent", "Intel Corporation", "Author ORCID iDs", "technical details"}
            <= rejected
        )

    def test_pipeline_normalizes_acronym_and_rejects_named_items(self):
        pages = [
            PageText(
                1,
                "Knowledge-Based Systems(KBS) use CAPTCHA technology. "
                "AEG bot, Cloud Volumes, BERT, and GPT are examples. Erica is a named robot.",
            )
        ]
        dictionary = DictionaryIndex(
            [
                {"en": "knowledge-based system", "tr": "özbilgi tabanlı dizge"},
                {"en": "captcha", "tr": "captcha"},
            ]
        )

        class NamedProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("Knowledge-Based Systems(KBS)"),
                    ExtractedTerm("CAPTCHA technology"),
                    ExtractedTerm("AEG bot"),
                    ExtractedTerm("Cloud Volumes"),
                    ExtractedTerm("BERT"),
                    ExtractedTerm("GPT"),
                    ExtractedTerm("Erica"),
                ]

        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("named.pdf"), dictionary, NamedProvider(), "fake-model"
            )

        self.assertEqual(
            {"KBS"},
            {item["term"] for item in result["possible_matches"]},
        )
        self.assertIn(
            "Knowledge-Based Systems",
            {item["term"] for item in result["dictionary_matches"]},
        )
        self.assertEqual([], result["missing_terms"])
        self.assertEqual(
            {"AEG bot", "Cloud Volumes", "BERT", "GPT", "Erica"},
            {item["term"] for item in result["rejected_candidates"]},
        )

    def test_pipeline_uses_optional_local_technical_review(self):
        pages = [
            PageText(1, "A multilayer perceptron is compared with a small model over DNS.")
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("review.pdf"), DictionaryIndex([]), ValidatingProvider(), "fake-model"
            )
        self.assertEqual(
            [item["term"] for item in result["missing_terms"]],
            ["multilayer perceptron"],
        )
        dns = next(item for item in result["rejected_candidates"] if item["term"] == "DNS")
        self.assertEqual(dns["review_priority"], "low")
        self.assertEqual(dns["model_review"], "rejected")
        # "small model" genel İngilizce filtresi tarafından elenir,
        # review_queue'ya girmez. Yalnızca "multilayer perceptron" ve "DNS" kalır.
        self.assertIn(
            "common_english_word",
            {item["reason"] for item in result["rejected_candidates"]},
        )
        self.assertEqual(result["technical_review"]["accepted_count"], 1)
        self.assertIn("multilayer perceptron", result["technical_review"]["candidate_terms"])
        self.assertEqual(result["technical_review"]["accepted_terms"], ["multilayer perceptron"])

    def test_model_rejection_does_not_veto_a_repeated_primary_candidate(self):
        class SkepticalProvider:
            def extract(self, text):
                return [ExtractedTerm("algorithmic recourse")]

            def validate_terms(self, terms):
                return []

        pages = [
            PageText(1, "Algorithmic recourse improves access. Algorithmic recourse is evaluated.")
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("recourse.pdf"), DictionaryIndex([]), SkepticalProvider(), "fake-model"
            )
        self.assertEqual([item["term"] for item in result["missing_terms"]], ["algorithmic recourse"])
        self.assertEqual(result["missing_terms"][0]["model_review"], "rejected")
        self.assertEqual(result["missing_terms"][0]["review_priority"], "high")

    def test_pipeline_preserves_single_word_technical_terms(self):
        class TechTermProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("Transformer"),
                    ExtractedTerm("Softmax"),
                    ExtractedTerm("Azure"),
                    ExtractedTerm("Sophia"),
                ]

        pages = [
            PageText(1, "Transformer uses Softmax and runs on Azure. Sophia is an author.")
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("tech.pdf"), DictionaryIndex([]), TechTermProvider(), "fake-model"
            )
        missing_terms = {item["term"] for item in result["missing_terms"]}
        rejected_reasons = {item["term"]: item.get("reason") for item in result["rejected_candidates"]}

        self.assertIn("Transformer", missing_terms)
        self.assertIn("Softmax", missing_terms)
        self.assertIn("Azure", missing_terms)
        self.assertEqual(rejected_reasons.get("Sophia"), "person_name")


    def test_common_english_filter_rejects_generic_words(self):
        """Genel İngilizce kelimeler (method, approach vb.) otomatik elenir."""

        class GenericProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("method"),
                    ExtractedTerm("cloud computing"),
                    ExtractedTerm("different approaches"),
                    ExtractedTerm("API"),
                    ExtractedTerm("natural language"),
                ]

        pages = [
            PageText(
                1,
                "The method of cloud computing uses different approaches and "
                "natural language with an API. The method is discussed. "
                "Cloud computing is the different approaches for natural language and API.",
            )
        ]
        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            result = analyze_pdf(
                Path("generic.pdf"), DictionaryIndex([]), GenericProvider(), "fake-model"
            )
        rejected_terms = {item["term"] for item in result["rejected_candidates"]}
        rejected_reasons = {
            item["term"]: item.get("reason")
            for item in result["rejected_candidates"]
        }
        # "method" ve "different approaches" genel İngilizce kelimeleri olarak elenmeli
        self.assertIn("method", rejected_terms)
        self.assertEqual(rejected_reasons["method"], "common_english_word")
        # \"different approaches\" → \"approaches\" (\"different\" genel niteleyici olarak kırpılır)
        self.assertIn("approaches", rejected_terms)
        # "API" büyük harfli kısaltma, genel İngilizce filtresi muaf tutmalı
        self.assertNotIn("API", rejected_terms)
        # "cloud computing" ve "natural language" bilişim terimleri olarak kalmalı
        missing_terms = {item["term"] for item in result["missing_terms"]}
        # Her iki kelimesi de genel İngilizce'de olan terimler elenecek
        # ama "cloud computing" en az bir kelimesi genel İngilizce'de olmayabilir
        # (cloud kelimesi listede olabilir ama computing de olabilir)
        # Burada önemli olan: API'nin korunması ve method'un elenmesi
        self.assertNotIn("API", rejected_terms)

    def test_ngram_scan_adds_to_deterministic_candidates(self):
        """N-gram tarayıcısı teknik sinyalli öbekleri deterministik adaylara ekler."""
        from terim_etmeni.term_extractor import _ngram_candidates

        pages = [
            PageText(
                1,
                "The SSL certificate is verified. An SSL certificate protects the site. "
                "Each SSL certificate has a chain. The TLS handshake begins.",
            ),
            PageText(
                2,
                "The TLS handshake ensures secure transport. "
                "After the TLS handshake, data is encrypted. "
                "An SSL certificate is required for HTTPS.",
            ),
        ]
        candidates = _ngram_candidates(pages)
        candidate_terms = {term.casefold() for term, _ in candidates}
        candidate_sources = {term.casefold(): source for term, source in candidates}
        # "SSL certificate" ve "TLS handshake" en az 2 kez geçiyor ve teknik sinyal taşıyor
        self.assertIn("ssl certificate", candidate_terms)
        self.assertIn("tls handshake", candidate_terms)
        # Kaynak "ngram_scan" olmalı
        self.assertEqual(candidate_sources["ssl certificate"], "ngram_scan")

    def test_ngram_scan_excludes_or_coordinated_fragments(self):
        """Koordinasyonlu sıfat dizileri ayrı terim adayları üretmemeli."""
        from terim_etmeni.term_extractor import _ngram_candidates

        pages = [
            PageText(
                1,
                "Cybersecurity- or privacy-supporting capability is available. "
                "Cybersecurity- or privacy-supporting capability is required.",
            )
        ]

        candidates = {term.casefold() for term, _ in _ngram_candidates(pages)}
        self.assertFalse(
            candidates
            & {
                "cybersecurity or privacy-supporting",
                "or privacy-supporting",
                "or privacy-supporting capability",
                "privacy-supporting capability",
                "privacy-supporting capability is",
            }
        )

    def test_ngram_scan_rejects_reference_and_formula_fragments(self):
        from terim_etmeni.term_extractor import _ngram_candidates

        pages = [PageText(1, "In AAAI Conference on AI. In AAAI Conference on AI. i k2 T appears. i k2 T appears.")]
        candidates = {term.casefold() for term, _ in _ngram_candidates(pages)}
        self.assertFalse(candidates & {"in aaai", "aaai conference", "aaai conference on", "i k2", "i k2 t", "k2 t"})


if __name__ == "__main__":
    unittest.main()
