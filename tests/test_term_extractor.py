import unittest

from terim_etmeni.models import ExtractedTerm, PageText, TextChunk
from terim_etmeni.term_extractor import extract_verified_terms


class FakeProvider:
    def extract(self, text):
        return [
            ExtractedTerm("Machine Learning"),
            ExtractedTerm("invented technology"),
            ExtractedTerm("neural-network"),
            ExtractedTerm("Section: This is a whole sentence presented as a term."),
            ExtractedTerm("AI in Education"),
            ExtractedTerm("Operational sequence"),
            ExtractedTerm("semantic router selects a worker"),
            ExtractedTerm("Adaptive Systems Research Note"),
            ExtractedTerm("experimental components"),
            ExtractedTerm("big oak"),
            ExtractedTerm("decision tree"),
            ExtractedTerm("binary search tree"),
            ExtractedTerm("spanning tree protocol"),
            ExtractedTerm("face recognition"),
            ExtractedTerm("star topology"),
            ExtractedTerm("star schema"),
            ExtractedTerm("forest root domain"),
            ExtractedTerm("x ∼ p(x)"),
            ExtractedTerm("DDPM"),
            ExtractedTerm("SML/PCD"),
            ExtractedTerm("DALL-E 2"),
            ExtractedTerm("Stable Diffusion model"),
            ExtractedTerm("ARTIC3D [YRH∗23]"),
            ExtractedTerm("Give him a cowboy hat"),
            ExtractedTerm("Theorem 4.1"),
            ExtractedTerm("f (θ)"),
            ExtractedTerm("INPUT PROJECTION OUTPUT"),
            ExtractedTerm("1epochCBOW 600"),
            ExtractedTerm("System TestFrameAccuracy"),
            ExtractedTerm("benchmark score"),
            ExtractedTerm("vector training accuracy"),
            ExtractedTerm("Currency Angola kwanza Iran rial"),
            ExtractedTerm("word vectors are well trained"),
            ExtractedTerm("between pre-training"),
            ExtractedTerm("is Service Provider"),
            ExtractedTerm("i-th token"),
        ]


class TermExtractorTests(unittest.TestCase):
    def test_deterministic_recovery_finds_model_omissions_without_raw_ngrams(self):
        class SilentProvider:
            def extract(self, text):
                return []

        pages = [
            PageText(
                1,
                "The Domain Name System (DNS) supports an adaptive signal router. "
                "Virtual customer assistance (VCA) is available. DNS protects the "
                "decision tree. A field of cardiology (CRG) is mentioned.",
            )
        ]
        chunks = [TextChunk(1, 0, pages[0].text)]

        evidence = extract_verified_terms(chunks, pages, SilentProvider())
        by_term = {item.term.casefold(): item for item in evidence}

        self.assertIn("adaptive signal router", by_term)
        self.assertIn("decision tree", by_term)
        self.assertIn("dns", by_term)
        self.assertIn("domain name system", by_term)
        self.assertIn("virtual customer assistance", by_term)
        self.assertIn("vca", by_term)
        self.assertNotIn("crg", by_term)
        self.assertIn(
            "technical_pattern",
            by_term["adaptive signal router"].candidate_sources,
        )
        self.assertIn("repeated_abbreviation", by_term["dns"].candidate_sources)

    def test_model_hallucinations_are_removed_and_evidence_is_counted(self):
        pages = [
            PageText(1, 'Machine learning uses a neural network and "quoted cache fabric".'),
            PageText(2, "Machine Learning and another neural-network. Operational sequence. A semantic router selects a worker. Adaptive Systems Research Note. Experimental components.\nA big oak appears beside a decision tree, binary search tree, spanning tree protocol, face recognition system, star topology, star schema, and forest root domain.\nDDPM and SML/PCD are listed beside a DALL-E 2 and a Stable Diffusion model. ARTIC3D [YRH∗23]. Give him a cowboy hat. Theorem 4.1 uses f (θ). INPUT PROJECTION OUTPUT. 1epochCBOW 600. System TestFrameAccuracy. benchmark score 50 10 20. vector training accuracy\nModel Vector Training Accuracy\nRow A 50 10 20\nRow B 60 30 40\nCurrency Angola kwanza Iran rial\nCity Chicago Illinois Stockton California\nPlural nouns mouse mice dollar dollars. word vectors are well trained."),
            PageText(3, "A big oak appears beside a decision tree, binary search tree, spanning tree protocol, face recognition system, star topology, star schema, and forest root domain. DDPM and SML/PCD are discussed."),
        ]
        chunks = [TextChunk(1, 0, pages[0].text), TextChunk(2, 1, pages[1].text)]

        results = extract_verified_terms(chunks, pages, FakeProvider())
        by_term = {item.term: item for item in results}

        self.assertNotIn("invented technology", by_term)
        self.assertNotIn("AI in Education", by_term)
        self.assertNotIn("Operational sequence", by_term)
        self.assertNotIn("semantic router selects a worker", by_term)
        self.assertNotIn("Adaptive Systems Research Note", by_term)
        self.assertNotIn("experimental components", by_term)
        # Görsel çağrışımlı sözcükler bağlamdan bağımsız elenmez; aksi halde
        # yerleşik bilişim terimleri sessizce kaybolur.
        self.assertIn("big oak", by_term)
        for term in (
            "decision tree",
            "binary search tree",
            "spanning tree protocol",
            "face recognition",
            "star topology",
            "star schema",
            "forest root domain",
        ):
            self.assertIn(term, by_term)
        self.assertNotIn("x ∼ p(x)", by_term)
        self.assertIn("DDPM", by_term)
        self.assertIn("SML/PCD", by_term)
        self.assertNotIn("DALL-E 2", by_term)
        self.assertNotIn("Stable Diffusion model", by_term)
        self.assertNotIn("ARTIC3D [YRH∗23]", by_term)
        self.assertNotIn("Give him a cowboy hat", by_term)
        self.assertNotIn("Theorem 4.1", by_term)
        self.assertNotIn("f (θ)", by_term)
        self.assertNotIn("INPUT PROJECTION OUTPUT", by_term)
        self.assertNotIn("1epochCBOW 600", by_term)
        self.assertNotIn("System TestFrameAccuracy", by_term)
        self.assertNotIn("benchmark score", by_term)
        self.assertNotIn("vector training accuracy", by_term)
        self.assertNotIn("Currency Angola kwanza Iran rial", by_term)
        self.assertNotIn("word vectors are well trained", by_term)
        self.assertNotIn("between pre-training", by_term)
        self.assertNotIn("is Service Provider", by_term)
        self.assertNotIn("i-th token", by_term)
        self.assertEqual(by_term["Machine Learning"].pages, {1, 2})
        self.assertEqual(by_term["Machine Learning"].occurrence_count, 2)
        self.assertEqual(by_term["neural-network"].pages, {1, 2})
        self.assertEqual(by_term["quoted cache fabric"].pages, {1})

    def test_failed_chunk_is_recorded_without_discarding_other_chunks(self):
        class PartlyFailingProvider:
            def extract(self, text):
                if "PAGE 2" in text:
                    raise RuntimeError("model response malformed")
                return [ExtractedTerm("machine learning")]

        pages = [
            PageText(1, "Machine learning appears here."),
            PageText(2, "Machine learning appears here too."),
        ]
        chunks = [TextChunk(1, 0, pages[0].text), TextChunk(2, 1, pages[1].text)]
        warnings = []
        evidence = extract_verified_terms(chunks, pages, PartlyFailingProvider(), warnings)
        self.assertEqual([item.term for item in evidence], ["machine learning"])
        self.assertEqual(len(warnings), 1)

    def test_code_variables_and_dataset_entities_are_rejected(self):
        class CodeNoiseProvider:
            def extract(self, text):
                return [
                    ExtractedTerm("num_heads"),
                    ExtractedTerm("frac_prevs(tokens,open)"),
                    ExtractedTerm("assume_bos"),
                    ExtractedTerm("batch_size"),
                    ExtractedTerm("Siberian husky"),
                    ExtractedTerm("space shuttle"),
                    ExtractedTerm("latent diffusion models"),
                ]

        pages = [
            PageText(
                1,
                "The num_heads and batch_size are configured in Python code. "
                "The function frac_prevs(tokens,open) sets assume_bos = True. "
                "Siberian husky and space shuttle are ImageNet classes. "
                "Latent diffusion models perform well.",
            )
        ]
        chunks = [TextChunk(1, 0, pages[0].text)]
        evidence = extract_verified_terms(chunks, pages, CodeNoiseProvider())
        terms = {item.term for item in evidence}

        self.assertIn("latent diffusion models", terms)
        self.assertNotIn("num_heads", terms)
        self.assertNotIn("frac_prevs(tokens,open)", terms)
        self.assertNotIn("assume_bos", terms)
        self.assertNotIn("batch_size", terms)
        self.assertNotIn("Siberian husky", terms)
        self.assertNotIn("space shuttle", terms)


if __name__ == "__main__":
    unittest.main()
