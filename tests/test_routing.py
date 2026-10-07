import unittest

from jev_router.routing import fixed_result, validate_result

CANDIDATES = {
    "fast": {"model": "model-a", "description": "簡單問題"},
    "deep": {"model": "model-b", "description": "複雜問題"},
}


class RoutingTests(unittest.TestCase):
    def response(self):
        return {"model": "jev-test", "answers": {"route": {
            "choice": "fast", "probabilities": {"fast": 0.9, "deep": 0.1}, "confidence": 0.8,
        }}}

    def test_recommendation_never_executes_model(self):
        result = validate_result(self.response(), CANDIDATES)
        self.assertEqual(result["recommended_model"], "model-a")
        self.assertFalse(result["selected_model_called"])

    def test_auto_send_uses_raw_confidence(self):
        for confidence, expected in ((0.7999, False), (0.8, True), (0.95, True)):
            with self.subTest(confidence=confidence):
                response = self.response()
                response["answers"]["route"]["confidence"] = confidence
                result = validate_result(response, CANDIDATES)
                self.assertEqual(result["auto_send"], expected)
                self.assertEqual(result["source"], "jev")

    def test_fixed_route_needs_existing_tier(self):
        result = fixed_result(CANDIDATES, "deep")
        self.assertEqual(result["recommended_model"], "model-b")
        self.assertIsNone(result["confidence"])
        self.assertTrue(result["auto_send"])
        self.assertFalse(result["selected_model_called"])
        with self.assertRaises(ValueError):
            fixed_result(CANDIDATES, "standard")

    def test_rejects_unknown_choice_invalid_numbers_and_missing_candidates(self):
        for field, value in (
            ("choice", "unknown"), ("choice", "deep"), ("confidence", float("nan")),
            ("confidence", True), ("probabilities", {"fast": 1}),
            ("probabilities", {"fast": 0.3, "deep": 0.2}),
        ):
            with self.subTest(field=field, value=value):
                response = self.response()
                response["answers"]["route"][field] = value
                with self.assertRaises(ValueError):
                    validate_result(response, CANDIDATES)
