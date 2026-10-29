import unittest

from backend.triage import EXAMPLES, evaluate_examples, triage_ticket


class TriageTests(unittest.TestCase):
    def test_bundled_examples_match_labels(self):
        report = evaluate_examples()

        self.assertEqual(report["sample_count"], len(EXAMPLES))
        self.assertEqual(report["category_accuracy"], 1.0)
        self.assertEqual(report["severity_accuracy"], 1.0)
        self.assertIn("in-sample", report["evaluation_type"])

    def test_unknown_issue_is_sent_to_manual_review(self):
        result = triage_ticket("Strange sound from the auxiliary pump", "hydro")

        self.assertEqual(result["category"], "manual_review")
        self.assertEqual(result["disposition"], "manual_review")
        self.assertEqual(result["confidence"], "low")

    def test_worsening_gearbox_vibration_is_critical(self):
        result = triage_ticket(
            "Gearbox vibration has increased with abnormal noise", "wind"
        )

        self.assertEqual(result["category"], "gearbox_vibration")
        self.assertEqual(result["severity"], "critical")
        self.assertEqual(result["disposition"], "routed")

    def test_immediate_safety_signal_overrides_category_baseline(self):
        result = triage_ticket("Smoke and fire reported near the solar array", "solar")

        self.assertEqual(result["severity"], "critical")
        self.assertEqual(result["category"], "manual_review")

    def test_result_includes_retrieval_and_auditable_steps(self):
        result = triage_ticket(EXAMPLES[0]["description"], EXAMPLES[0]["asset_type"])

        self.assertTrue(result["evidence"]["is_reference_example"])
        self.assertEqual(result["evidence"]["ticket_id"], "T001")
        self.assertEqual(result["agent_steps"][-1]["tool"], "routing_policy")


if __name__ == "__main__":
    unittest.main()