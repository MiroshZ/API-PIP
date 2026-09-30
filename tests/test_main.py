import json
import tempfile
import unittest
from pathlib import Path

from main import ReviewAnalysis, load_reviews, save_result


class PipelineTests(unittest.TestCase):
    def test_load_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reviews.csv"
            source.write_text('id,text\n1,"Отличный товар"\n', encoding="utf-8")

            reviews = load_reviews(source)

            self.assertEqual(reviews[0].id, "1")
            self.assertEqual(reviews[0].text, "Отличный товар")

    def test_duplicate_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reviews.csv"
            source.write_text("id,text\n1,Первый\n1,Второй\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate id"):
                load_reviews(source)

    def test_malformed_csv_row_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reviews.csv"
            source.write_text("id,text\n1,Первый,лишнее поле\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "wrong number of CSV fields"):
                load_reviews(source)

    def test_save_result_creates_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            result = ReviewAnalysis(
                id="1",
                sentiment="positive",
                topic="product_quality",
                confidence=0.9,
            )

            save_result(output, Path("reviews.csv"), "test-model", [result])
            document = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(document["metadata"]["items_count"], 1)
            self.assertEqual(document["results"][0]["sentiment"], "positive")


if __name__ == "__main__":
    unittest.main()
