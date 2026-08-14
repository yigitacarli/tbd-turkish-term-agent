import json
import tempfile
import unittest
from pathlib import Path

from terim_etmeni.reporting import report_rows, write_reports


class ReportingTests(unittest.TestCase):
    def test_write_reports_creates_two_sheet_xlsx_and_csv(self):
        result = {
            "document": "test_doc.pdf",
            "model": "test-model",
            "dictionary_version": "2026-07-20",
            "missing_terms": [
                {
                    "term": "soft state",
                    "context": "Nodes maintain soft state across rounds.",
                    "pages": [8],
                    "occurrence_count": 2,
                    "review_priority": "high",
                }
            ],
            "dictionary_matches": [
                {
                    "term": "distributed systems",
                    "translations": ["dağıtımlı dizge"],
                    "match_type": "singular_variant",
                    "context": "Distributed systems scale horizontally.",
                    "pages": [1, 2],
                    "occurrence_count": 10,
                }
            ],
            "possible_matches": [
                {
                    "term": "RBAC",
                    "possible_dictionary_terms": [
                        {"en": "Role-Based Access Control", "tr": "role dayalı erişim denetimi"}
                    ],
                    "context": "RBAC policy is enforced.",
                    "pages": [5],
                    "occurrence_count": 1,
                }
            ],
            "rejected_candidates": [],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            json_path, csv_path = write_reports(result, Path(tmp_dir))
            xlsx_path = json_path.with_name("test_doc_terim_raporu.xlsx")

            self.assertTrue(json_path.is_file())
            self.assertTrue(csv_path.is_file())
            self.assertTrue(xlsx_path.is_file())

            # CSV içeriği kontrolü
            csv_content = csv_path.read_text(encoding="utf-8-sig")
            self.assertIn("soft state", csv_content)
            self.assertIn("Nodes maintain soft state across rounds.", csv_content)
            self.assertIn("Makaledeki Bağlam (Örnek Cümle)", csv_content)

            # XLSX sayfaları kontrolü
            import openpyxl
            wb = openpyxl.load_workbook(xlsx_path)
            self.assertEqual(wb.sheetnames, ["Eksik Terimler (İnceleme)", "Sözlükte Bulunanlar"])
            ws1 = wb["Eksik Terimler (İnceleme)"]
            self.assertEqual(ws1["B5"].value, "soft state")
            self.assertIn("soft state", str(ws1["C5"].value))


if __name__ == "__main__":
    unittest.main()
