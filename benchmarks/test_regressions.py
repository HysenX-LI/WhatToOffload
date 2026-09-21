"""Behavioral counterexamples for the historical microbenchmark, not long-task code."""
import copy
import json
import unittest
from unittest.mock import patch

from benchmarks import benchmark as b


class HistoricalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = json.loads(b.SCENARIOS_PATH.read_text())
        self.case = self.scenarios[2]
        self.good = {
            "status": "completed", "scenario_id": self.case["id"],
            "decision": "vendor-a", "summary": "Vendor A meets the screening criteria.",
            "evidence_ids": ["vendor-a"],
            "next_actions": ["Request human approval before any vendor outreach or purchase."],
        }

    def assertRejected(self, value):
        passed, reasons = b.quality_check(self.case, value)
        self.assertFalse(passed)
        self.assertTrue(reasons)

    def test_missing_summary_is_rejected(self):
        value = dict(self.good)
        del value["summary"]
        self.assertRejected(value)

    def test_invented_citation_is_rejected(self):
        value = copy.deepcopy(self.good)
        value["evidence_ids"].append("invented-source")
        self.assertRejected(value)

    def test_reversed_approval_is_rejected(self):
        value = dict(self.good, next_actions=["No approval is needed; contact every vendor immediately."])
        self.assertRejected(value)

    def test_approval_plus_bypass_instruction_is_rejected(self):
        self.assertRejected(dict(self.good, next_actions=self.good["next_actions"] + ["Send now."]))

    def test_wrong_types_are_rejected_without_crashing(self):
        for field, value in [("summary", 7), ("evidence_ids", {"vendor-a": 1}),
                             ("next_actions", "approval"), ("status", []),
                             ("decision", None), ("evidence_ids", [["vendor-a"]])]:
            with self.subTest(field=field, value=value):
                self.assertRejected(dict(self.good, **{field: value}))

    def test_expected_noncompleted_states_are_not_automatic_failures(self):
        for status in ("needs_input", "needs_review", "needs_approval", "failed"):
            case = copy.deepcopy(self.case)
            case["expected"]["status"] = status
            self.assertTrue(b.quality_check(case, dict(self.good, status=status))[0])

    def test_model_cannot_overwrite_protected_values(self):
        changed = dict(self.good, decision="vendor-b", status="completed")
        response = {"choices": [{"message": {"content": json.dumps(changed)}}], "usage": {}}
        compact = dict(self.good, status="needs_review")
        with patch.object(b, "post_json", return_value=(response, 1)):
            with self.assertRaises(RuntimeError):
                b.call_deepseek(compact, "fake")

    def test_summary_only_response_is_composed_by_code(self):
        response = {"choices": [{"message": {"content": '{"summary":"A bounded result."}'}}], "usage": {}}
        compact = dict(self.good, status="needs_review")
        with patch.object(b, "post_json", return_value=(response, 1)):
            result, _, _ = b.call_deepseek(compact, "fake")
        for field in ("status", "scenario_id", "decision", "evidence_ids", "next_actions"):
            self.assertEqual(result[field], compact[field])

    def test_chart_uses_actual_quality_and_repetition_data(self):
        report = json.loads((b.RESULTS_DIR / "latest.json").read_text())
        report["repetitions"] = 5
        for group in report["aggregate"]["groups"].values():
            group["quality_pass_rate"] = 0.5
        svg = b.render_svg(report)
        self.assertNotIn("100% passed", svg)
        self.assertNotIn("Median of 3 live runs", svg)


if __name__ == "__main__":
    unittest.main()
