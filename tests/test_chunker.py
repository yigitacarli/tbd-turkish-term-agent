import unittest

from terim_etmeni.chunker import chunk_pages
from terim_etmeni.models import PageText


class ChunkerTests(unittest.TestCase):
    def test_chunks_preserve_page_numbers_and_size(self):
        pages = [PageText(1, "First sentence. " * 40), PageText(2, "Second page.")]
        chunks = chunk_pages(pages, size=220, overlap=20)

        self.assertGreater(len(chunks), 2)
        self.assertEqual(chunks[0].page, 1)
        self.assertEqual(chunks[-1].page, 2)
        self.assertEqual([chunk.index for chunk in chunks], list(range(len(chunks))))

    def test_invalid_overlap_is_rejected(self):
        with self.assertRaises(ValueError):
            chunk_pages([PageText(1, "text")], size=200, overlap=200)


if __name__ == "__main__":
    unittest.main()
