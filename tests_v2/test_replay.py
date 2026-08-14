import json
import tempfile
import unittest
from pathlib import Path

from terim_etmeni.dictionary import DictionaryIndex
from terim_etmeni.models import ExtractedTerm, PageText, TermEvidence
from terim_etmeni.pipeline import analyze_pdf
from terim_etmeni_v2.abbreviation_index import AbbreviationIndex
from terim_etmeni_v2.cli import main
from terim_etmeni_v2.replay import (
    ReplayError,
    build_candidate_snapshot,
    load_candidate_snapshot,
    replay_snapshot,
    write_candidate_snapshot,
)


class ReplayTests(unittest.TestCase):
    def snapshot(self, accepted=("algorithmic recourse",)):
        pages = [
            PageText(
                1,
                "Machine learning supports algorithmic recourse. "
                "Algorithmic recourse improves decisions.",
            )
        ]
        return build_candidate_snapshot(
            document="article.pdf",
            model="qwen3.5:2b",
            pages=pages,
            model_evidence=[
                TermEvidence(
                    term="machine learning",
                    pages={1},
                    occurrence_count=1,
                    candidate_sources={"model"},
                ),
                TermEvidence(
                    term="algorithmic recourse",
                    pages={1},
                    occurrence_count=2,
                    candidate_sources={"model"},
                ),
            ],
            chunk_count=1,
            processed_chunk_count=1,
            technical_review_accepted_terms=accepted,
        )

    def test_snapshot_round_trip_and_replay_do_not_call_ollama(self):
        dictionary = DictionaryIndex(
            [{"en": "machine learning", "tr": "makine öğrenmesi"}],
            metadata={"version": "2026-08-13"},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            write_candidate_snapshot(self.snapshot(), path)
            result = replay_snapshot(load_candidate_snapshot(path), dictionary)

        self.assertEqual(result["counts"]["dictionary_matches"], 1)
        self.assertEqual(result["counts"]["missing_terms"], 1)
        self.assertEqual(result["missing_terms"][0]["term"], "algorithmic recourse")
        self.assertEqual(result["dictionary_version"], "2026-08-13")
        self.assertTrue(result["replay"]["enabled"])
        self.assertFalse(result["replay"]["ollama_called"])

    def test_fixed_review_decision_is_replayed(self):
        result = replay_snapshot(self.snapshot(accepted=()), DictionaryIndex([]))
        rejected = {item["term"] for item in result["rejected_candidates"]}
        self.assertNotIn("algorithmic recourse", rejected)
        # İki geçiş ve model kaynağı, model reddine rağmen güçlü kanıtı korur.
        self.assertIn(
            "algorithmic recourse",
            {item["term"] for item in result["missing_terms"]},
        )

    def test_v2_keeps_distributed_system_transparency_terms(self):
        pages = [PageText(1, "Access transparency and location transparency are required.")]
        snapshot = build_candidate_snapshot(
            document="distributed.pdf",
            model="qwen3.5:2b",
            pages=pages,
            model_evidence=[
                TermEvidence(
                    term="access transparency",
                    pages={1},
                    occurrence_count=1,
                    candidate_sources={"model"},
                ),
                TermEvidence(
                    term="location transparency",
                    pages={1},
                    occurrence_count=1,
                    candidate_sources={"model"},
                ),
            ],
            chunk_count=1,
            processed_chunk_count=1,
            technical_review_accepted_terms=(
                "access transparency",
                "location transparency",
            ),
        )
        result = replay_snapshot(snapshot, DictionaryIndex([]))
        self.assertEqual(
            {item["term"] for item in result["missing_terms"]},
            {"access transparency", "location transparency"},
        )

    def test_v2_keeps_only_reviewed_titlecase_technical_patterns(self):
        pages = [
            PageText(
                1,
                "Asymmetric Encryption uses a Merkle Tree, not concerns authorization.",
            )
        ]
        snapshot = build_candidate_snapshot(
            document="technical-headings.pdf",
            model="qwen3.5:2b",
            pages=pages,
            model_evidence=[
                TermEvidence(
                    term=term,
                    pages={1},
                    occurrence_count=1,
                    candidate_sources={"technical_pattern"},
                )
                for term in (
                    "Asymmetric Encryption",
                    "Merkle Tree",
                    "concerns authorization",
                )
            ],
            chunk_count=1,
            processed_chunk_count=1,
            technical_review_accepted_terms=(
                "Asymmetric Encryption",
                "Merkle Tree",
                "concerns authorization",
            ),
        )
        result = replay_snapshot(snapshot, DictionaryIndex([]))

        self.assertEqual(
            {item["term"] for item in result["missing_terms"]},
            {"Asymmetric Encryption", "Merkle Tree"},
        )
        rejected = {item["term"] for item in result["rejected_candidates"]}
        self.assertIn("concerns authorization", rejected)

    def test_v2_keeps_only_reviewed_acronym_ngrams(self):
        pages = [
            PageText(
                1,
                "Network-based IDS uses an SNMP trap and GPS masters, not CPU power.",
            )
        ]
        snapshot = build_candidate_snapshot(
            document="acronym-ngrams.pdf",
            model="qwen3.5:2b",
            pages=pages,
            model_evidence=[
                TermEvidence(
                    term=term,
                    pages={1},
                    occurrence_count=1,
                    candidate_sources={"ngram_scan"},
                )
                for term in (
                    "network-based IDS",
                    "SNMP trap",
                    "GPS masters",
                    "CPU power",
                    "prevent double-spending",
                )
            ],
            chunk_count=1,
            processed_chunk_count=1,
            technical_review_accepted_terms=(
                "network-based IDS",
                "SNMP trap",
                "GPS masters",
                "prevent double-spending",
            ),
        )
        result = replay_snapshot(snapshot, DictionaryIndex([]))

        self.assertEqual(
            {item["term"] for item in result["missing_terms"]},
            {"network-based IDS", "SNMP trap", "GPS masters"},
        )
        rejected = {item["term"] for item in result["rejected_candidates"]}
        self.assertIn("CPU power", rejected)
        self.assertIn("prevent double-spending", rejected)

    def test_v2_keeps_recurring_multiword_common_english_phrases(self):
        pages = [
            PageText(
                1,
                "A read lock and a write lock protect the operation log. "
                "The operation log stores the read lock and write lock records.",
            )
        ]
        evidence = [
            TermEvidence(
                term=term,
                pages={1},
                occurrence_count=occurrence_count,
                candidate_sources={"model"},
            )
            for term, occurrence_count in (
                ("read lock", 2),
                ("write lock", 2),
                ("operation log", 2),
                ("client originated requests", 1),
            )
        ]
        snapshot = build_candidate_snapshot(
            document="locks.pdf",
            model="qwen3.5:2b",
            pages=pages,
            model_evidence=evidence,
            chunk_count=1,
            processed_chunk_count=1,
            technical_review_accepted_terms=(),
        )
        result = replay_snapshot(snapshot, DictionaryIndex([]))

        self.assertEqual(
            {item["term"] for item in result["missing_terms"]},
            {"read lock", "write lock", "operation log"},
        )
        rejected = {item["term"] for item in result["rejected_candidates"]}
        self.assertIn("client originated requests", rejected)

    def test_v2_keeps_only_reviewed_model_plurals(self):
        pages = [
            PageText(
                1,
                "Rulesets use accessors, allocators, and storage protocols.",
            )
        ]
        evidence = [
            TermEvidence(
                term=term,
                pages={1},
                occurrence_count=1,
                candidate_sources=sources,
            )
            for term, sources in (
                ("rulesets", {"model"}),
                ("accessors", {"model"}),
                ("allocators", {"model"}),
                ("storage protocols", {"technical_pattern"}),
            )
        ]
        snapshot = build_candidate_snapshot(
            document="reviewed-plurals.pdf",
            model="qwen3.5:2b",
            pages=pages,
            model_evidence=evidence,
            chunk_count=1,
            processed_chunk_count=1,
            technical_review_accepted_terms=(
                "rulesets",
                "accessors",
                "storage protocols",
            ),
        )
        result = replay_snapshot(snapshot, DictionaryIndex([]))

        self.assertEqual(
            {item["term"] for item in result["missing_terms"]},
            {"rulesets", "accessors"},
        )
        rejected = {item["term"] for item in result["rejected_candidates"]}
        self.assertIn("allocators", rejected)
        self.assertIn("storage protocols", rejected)

    def test_separate_abbreviation_source_keeps_ambiguity_and_defined_class(self):
        abbreviations = AbbreviationIndex(
            [
                {
                    "abbreviation": "AI",
                    "expansion": "Artificial Intelligence",
                    "turkish": "yapay zekâ",
                    "source_page": 3,
                },
                {
                    "abbreviation": "AI",
                    "expansion": "Asset Identification",
                    "turkish": "varlık tanımlaması",
                    "source_page": 4,
                },
            ],
            metadata={
                "version": "2025-03-17",
                "source_sha256": "abc",
                "raw_record_count": 2,
                "unique_abbreviation_count": 1,
            },
        )
        snapshot = build_candidate_snapshot(
            document="defined-abbreviation.pdf",
            model="qwen3.5:2b",
            pages=[
                PageText(
                    1,
                    "Artificial Intelligence (AI) systems use AI techniques.",
                )
            ],
            model_evidence=[
                TermEvidence(
                    term="AI",
                    pages={1},
                    occurrence_count=2,
                    candidate_sources={"repeated_abbreviation"},
                )
            ],
            chunk_count=1,
            processed_chunk_count=1,
            technical_review_accepted_terms=(),
        )
        result = replay_snapshot(snapshot, DictionaryIndex([]), abbreviations)

        self.assertEqual(result["counts"]["possible_matches"], 1)
        item = result["possible_matches"][0]
        self.assertEqual(item["match_type"], "defined_abbreviation")
        self.assertEqual(item["match_source"], "tbd_abbreviations")
        self.assertEqual(
            item["possible_abbreviation_terms"][0]["expansion"],
            "Artificial Intelligence",
        )
        self.assertEqual(len(item["possible_abbreviation_terms"]), 1)
        self.assertEqual(
            result["abbreviation_source"]["version"], "2025-03-17"
        )

    def test_undefined_abbreviation_remains_an_ambiguous_possible_match(self):
        abbreviations = AbbreviationIndex(
            [
                {"abbreviation": "AI", "expansion": "Artificial Intelligence", "turkish": "yapay zekâ"},
                {"abbreviation": "AI", "expansion": "Asset Identification", "turkish": "varlık tanımlaması"},
            ]
        )
        snapshot = build_candidate_snapshot(
            document="ambiguous-abbreviation.pdf",
            model="qwen3.5:2b",
            pages=[PageText(1, "AI techniques use AI models.")],
            model_evidence=[
                TermEvidence(
                    term="AI",
                    pages={1},
                    occurrence_count=2,
                    candidate_sources={"repeated_abbreviation"},
                )
            ],
            chunk_count=1,
            processed_chunk_count=1,
            technical_review_accepted_terms=(),
        )
        result = replay_snapshot(snapshot, DictionaryIndex([]), abbreviations)

        item = result["possible_matches"][0]
        self.assertEqual(item["match_type"], "abbreviation_source")
        self.assertEqual(len(item["possible_abbreviation_terms"]), 2)

    def test_invalid_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            with self.assertRaises(ReplayError):
                load_candidate_snapshot(path)

    def test_replay_matches_current_pipeline_for_the_same_model_candidates(self):
        class Provider:
            def extract(self, text):
                return [
                    ExtractedTerm("machine learning"),
                    ExtractedTerm("algorithmic recourse"),
                    ExtractedTerm("task"),
                ]

            def validate_terms(self, terms):
                return ["algorithmic recourse"]

        pages = [
            PageText(
                1,
                "Machine learning supports algorithmic recourse. "
                "Algorithmic recourse improves decisions. The task ends.",
            )
        ]
        dictionary = DictionaryIndex(
            [{"en": "machine learning", "tr": "makine öğrenmesi"}],
            metadata={"version": "test"},
        )
        from unittest.mock import patch
        from terim_etmeni_v2.replay import capture_candidate_snapshot

        with patch("terim_etmeni.pipeline.read_pdf", return_value=pages):
            current = analyze_pdf(
                Path("article.pdf"), dictionary, Provider(), "qwen3.5:2b"
            )
        with patch("terim_etmeni_v2.replay.read_pdf", return_value=pages):
            snapshot = capture_candidate_snapshot(
                Path("article.pdf"), dictionary, Provider(), "qwen3.5:2b", 6000, 100
            )
        replayed = replay_snapshot(snapshot, dictionary)

        for group in (
            "dictionary_matches",
            "possible_matches",
            "missing_terms",
            "rejected_candidates",
        ):
            self.assertEqual(replayed[group], current[group])
        self.assertEqual(replayed["counts"], current["counts"])

    def test_failed_technical_review_keeps_candidates_and_marks_partial(self):
        class Provider:
            def extract(self, text):
                return [ExtractedTerm("algorithmic recourse")]

            def validate_terms(self, terms):
                raise RuntimeError("review timeout")

        pages = [PageText(1, "Algorithmic recourse improves decisions twice. Algorithmic recourse.")]
        from unittest.mock import patch
        from terim_etmeni_v2.replay import capture_candidate_snapshot

        with patch("terim_etmeni_v2.replay.read_pdf", return_value=pages):
            snapshot = capture_candidate_snapshot(
                Path("article.pdf"), DictionaryIndex([]), Provider(), "qwen3.5:2b", 6000, 100
            )
        result = replay_snapshot(snapshot, DictionaryIndex([]))

        self.assertIsNone(snapshot["technical_review_accepted_terms"])
        self.assertEqual(result["analysis_status"], "partial")
        self.assertEqual(result["technical_review"]["status"], "failed")
        self.assertEqual(result["missing_terms"][0]["model_review"], "unavailable")

    def test_replay_cli_writes_explicit_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dictionary = root / "dictionary.json"
            dictionary.write_text(
                json.dumps(
                    {
                        "metadata": {"version": "test"},
                        "terms": [{"en": "machine learning", "tr": "YZ"}],
                    }
                ),
                encoding="utf-8",
            )
            abbreviations = root / "abbreviations.json"
            abbreviations.write_text(
                json.dumps({"metadata": {}, "abbreviations": []}),
                encoding="utf-8",
            )
            snapshot = write_candidate_snapshot(
                self.snapshot(), root / "snapshot.json"
            )
            output = root / "replay.json"
            from unittest.mock import patch

            with patch(
                "terim_etmeni_v2.cli.Settings",
                return_value=__import__(
                    "terim_etmeni_v2.config", fromlist=["Settings"]
                ).Settings(
                    bootstrap_dictionary=dictionary,
                    bootstrap_abbreviations=abbreviations,
                    dictionary_state_dir=root / "state",
                    output_dir=root / "output",
                ),
            ):
                code = main(["replay", str(snapshot), "--output", str(output)])
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertTrue(payload["replay"]["enabled"])


if __name__ == "__main__":
    unittest.main()
