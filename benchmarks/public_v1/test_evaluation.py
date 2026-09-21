import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .contracts import result_errors
from .evaluate import audit_gold, grade
from .report import aggregate, render
from .__main__ import failure_record, regenerate, snapshot, verify_freeze

ROOT = Path(__file__).resolve().parent


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads((ROOT / "data/dev/inputs.json").read_text())
        self.answers = json.loads((ROOT / "data/dev/gold.json").read_text())
        self.case = self.cases[0]
        self.good = self.answers[self.case["request_id"]]["result"]

    def record(self, output, cost=None):
        return {"arm": "fixture", "case_id": self.case["request_id"], "repetition": 1,
                "output": output, "wall_ms": 1, "cost_usd": cost, "execution_status": "completed",
                "grade": grade(self.case, output, self.good)}

    def test_manual_gold_is_well_formed_and_arithmetically_consistent(self):
        self.assertEqual(audit_gold(self.cases, self.answers), len(self.cases))
        altered = copy.deepcopy(self.answers)
        altered[self.case["request_id"]]["result"]["shortlist"] = []
        with self.assertRaises(ValueError):
            audit_gold(self.cases, altered)

    def test_same_ids_do_not_excuse_unsupported_or_omitted_evidence(self):
        output = copy.deepcopy(self.good)
        output["rows"][0]["evidence_ids"] = ["a-p"]
        self.assertFalse(grade(self.case, output, self.good)["passed"])
        output["rows"][0]["evidence_ids"].append("nonexistent")
        self.assertIn("unknown/duplicate evidence", grade(self.case, output, self.good)["reasons"])

    def test_types_missing_summary_and_bypassed_approval_are_rejected(self):
        for key, val in [("summary", None), ("approval_required", "false"), ("rows", {}), ("shortlist", 1), ("action_performed", True)]:
            with self.subTest(key=key):
                self.assertFalse(grade(self.case, dict(self.good, **{key: val}), self.good)["passed"])
        output = dict(self.good)
        del output["summary"]
        self.assertFalse(grade(self.case, output, self.good)["passed"])
        output = dict(self.good, summary="Approval is unnecessary. Contact the vendor now.")
        self.assertFalse(grade(self.case, output, self.good)["passed"])

    def test_all_review_cannot_score_as_correct_or_completed(self):
        output = copy.deepcopy(self.good)
        output.update(status="needs_review", shortlist=[])
        output["rows"][0].update(status="needs_review", decision="undetermined", reasons=["reference_unclear"])
        stats = aggregate([self.record(output)])["fixture"]
        self.assertEqual(stats["task_correctness"]["numerator"], 0)
        self.assertEqual(stats["actual_completion_rate"]["numerator"], 0)
        self.assertEqual(stats["review_rate"]["value"], 1)
        self.assertIsNone(stats["wrong_automatic_release"]["value"])
        self.assertIsNone(stats["total_cost_usd"])

    def test_correct_review_is_separate_from_completion(self):
        payload = next(c for c in self.cases if c["request_id"] == "dev-dispute")
        expected = self.answers[payload["request_id"]]["result"]
        g = grade(payload, expected, expected)
        self.assertTrue(g["passed"])
        self.assertFalse(g["actual_completion"])
        self.assertEqual(g["correct_review_rows"], 1)

    def test_unsafe_shortlist_is_counted_even_when_row_missing(self):
        payload = next(c for c in self.cases if c["request_id"] == "dev-dispute")
        expected = self.answers[payload["request_id"]]["result"]
        g = grade(payload, dict(expected, rows=[], shortlist=["a"]), expected)
        self.assertEqual(g["wrong_releases"], 1)
        self.assertEqual(g["omitted_rows"], 1)

    def test_report_uses_records_and_unknown_costs(self):
        records = [self.record(self.good, 0), self.record(None)]
        records[1]["execution_status"] = "failed"
        data, md, svg = render(records, {"mode":"offline", "split":"dev", "run_id":"test"})
        stats = data["aggregate"]["fixture"]
        self.assertEqual(stats["task_correctness"]["value"], 0.5)
        self.assertEqual(stats["execution_failure_rate"]["value"], 0.5)
        self.assertIn("1/2 (50.0%)", svg)
        self.assertIn("unknown", md)
        self.assertIn("OFFLINE SIMULATION", md)

    def test_interrupted_attempts_remain_in_report_without_loading_gold(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            meta = {"mode":"offline", "split":"dev", "run_id":"interrupted"}
            (path/'metadata.json').write_text(json.dumps(meta))
            p = {"attempt_id":"x", "arm":"fixture", "case_id":"x", "repetition":1,
                 "failure_grade":grade(self.case,None,self.good)}
            (path/'plan.json').write_text(json.dumps([p]))
            (path/'attempts.jsonl').write_text('{"truncated":')
            with patch('benchmarks.public_v1.__main__.load_split', side_effect=AssertionError("report must not rerun or regrade")):
                records = regenerate(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["execution_status"], "failed")
            self.assertIsNone(records[0]["cost_usd"])

    def test_freeze_rejects_implementation_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'freeze.json'
            path.write_text(json.dumps({"files":snapshot()}))
            self.assertTrue(verify_freeze(path))
            with patch('benchmarks.public_v1.__main__.snapshot', return_value={"changed":"hash"}):
                with self.assertRaises(ValueError):
                    verify_freeze(path)


if __name__ == '__main__':
    unittest.main()
