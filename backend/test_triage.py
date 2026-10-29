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

    def test_negated_safety_signal_does_not_override_active_fault(self):
        result = triage_ticket(
            "No fire or smoke observed; inverter has a high temperature alarm", "solar"
        )

        self.assertEqual(result["category"], "inverter_thermal")
        self.assertEqual(result["severity"], "high")

    def test_contrast_clause_keeps_active_safety_signal(self):
        result = triage_ticket(
            "No fire, but smoke observed near the inverter", "solar"
        )

        self.assertEqual(result["severity"], "critical")

    def test_not_detected_safety_signal_is_ignored(self):
        result = triage_ticket("Smoke was not detected near the array", "solar")

        self.assertEqual(result["severity"], "medium")
        self.assertEqual(result["category"], "manual_review")

    def test_cleared_alarm_is_not_routed_as_an_active_fault(self):
        result = triage_ticket(
            "No overheating; inverter thermal alarm cleared and normal", "solar"
        )

        self.assertEqual(result["category"], "manual_review")
        self.assertEqual(result["severity"], "medium")
        self.assertEqual(result["disposition"], "manual_review")

    def test_not_reflected_grid_instruction_is_still_an_active_mismatch(self):
        result = triage_ticket(
            "Curtailment instruction not reflected in generation dashboard", "grid"
        )

        self.assertEqual(result["category"], "grid_curtailment")
        self.assertEqual(result["disposition"], "routed")

    def test_result_includes_retrieval_and_auditable_steps(self):
        result = triage_ticket(EXAMPLES[0]["description"], EXAMPLES[0]["asset_type"])

        self.assertTrue(result["evidence"]["is_reference_example"])
        self.assertEqual(result["evidence"]["ticket_id"], "T001")
        self.assertEqual(result["agent_steps"][-1]["tool"], "routing_policy")


if __name__ == "__main__":
    unittest.main()