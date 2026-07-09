import sys
import types
import unittest


fake_ollama = types.SimpleNamespace(Client=lambda host=None: None)
sys.modules.setdefault("ollama", fake_ollama)

from transformer.recommender import _clean_response


class RecommenderFormatTests(unittest.TestCase):
    def test_clean_response_removes_echoed_question_prefix(self):
        raw = (
            "User's question: Should I exercise outside today?\n\n"
            "Recommendation: It's a good day for a light walk and a few easy stretches."
        )

        cleaned = _clean_response(raw)

        self.assertNotIn("User's question", cleaned)
        self.assertNotIn("Recommendation:", cleaned)
        self.assertTrue(cleaned.startswith("It's a good day"))
        self.assertNotIn("Should I exercise outside today?", cleaned)


if __name__ == "__main__":
    unittest.main()
