import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import benchmarks.test_audit_log as audit_fixture
from scripts.generate_gap_attribution import generate_report


ROOT = Path(__file__).resolve().parents[1]


def audit_event(seq, event_type, stage, **values):
    item = {"schema_version": 1, "run_id": "run-1", "event_id": f"event-{seq}", "seq": seq, "workflow_version": "workflow-v1", "stage": stage, "event_type": event_type, "status": "completed"}
    item.update(values)
    return item


def reference(**field_values):
    field = {"subject_ref": "sha256:" + "b" * 64, "field": "email", "expected_status": "available"}
    field.update(field_values)
    return {"schema_version": 1, "reference_version": "reference-v1", "fields": [field]}


class GapAttributionTests(unittest.TestCase):
    def assert_cause(self, events, frozen_reference, stage, cause):
        report = generate_report(events, frozen_reference)
        self.assertEqual(1, report["summary"]["gaps"])
        self.assertEqual(stage, report["gaps"][0]["primary_stage"])
        self.assertEqual(cause, report["gaps"][0]["primary_cause"])

    def test_attributes_each_major_stage_by_earliest_cause(self):
        cases = [
            ([audit_event(1, "field_missing", "assemble", field="email", reason_code="source_not_discovered")], {}, "discover", "source_not_discovered"),
            ([audit_event(1, "source_declared", "discover", source_id="source-1"), audit_event(2, "field_missing", "assemble", field="email", reason_code="fetch_failed")], {"expected_source_ids": ["source-1"]}, "retrieve", "fetch_failed"),
            ([audit_event(1, "source_declared", "discover", source_id="source-1"), audit_event(2, "source_retrieved", "retrieve", source_id="source-1"), audit_event(3, "field_missing", "assemble", field="email", reason_code="parser_unsupported")], {"expected_source_ids": ["source-1"]}, "parse", "parser_unsupported"),
            ([audit_event(1, "source_declared", "discover", source_id="source-1"), audit_event(2, "source_retrieved", "retrieve", source_id="source-1"), audit_event(3, "field_missing", "assemble", field="email", reason_code="candidate_omitted")], {"expected_source_ids": ["source-1"], "expected_candidate_ids": ["candidate-1"]}, "normalize", "candidate_omitted"),
            ([audit_event(1, "candidate_declared", "normalize", candidate_id="candidate-1"), audit_event(2, "field_missing", "assemble", field="email", reason_code="context_omission")], {"expected_candidate_ids": ["candidate-1"]}, "pack", "context_omission"),
            ([audit_event(1, "candidate_declared", "normalize", candidate_id="candidate-1"), audit_event(2, "context_packed", "pack", candidate_ids=["candidate-1"]), audit_event(3, "decision_recorded", "judge", field="email", candidate_ids=["candidate-1"], decision={"outcome": "reject", "reason_code": "below_threshold"}), audit_event(4, "field_rejected", "accept", field="email", reason_code="below_threshold")], {"expected_candidate_ids": ["candidate-1"]}, "judge", "below_threshold"),
            ([audit_event(1, "field_accepted", "accept", field="email", candidate_id="candidate-1", evidence_refs=["evidence-1"]), audit_event(2, "evidence_replaced", "repair", field="email", fields=["email"], evidence_id="evidence-2", prior_evidence_ids=["evidence-1"], reason_code="repair_rejected"), audit_event(3, "field_missing", "assemble", field="email", reason_code="repair_rejected")], {}, "repair", "repair_rejected"),
            ([audit_event(1, "decision_recorded", "judge", field="email", candidate_ids=["candidate-1"], decision={"outcome": "accept", "reason_code": "above_threshold"}), audit_event(2, "field_accepted", "accept", field="email", candidate_id="candidate-1", evidence_refs=["evidence-1"]), audit_event(3, "field_missing", "assemble", field="email", reason_code="assembly_drop")], {}, "assemble", "assembly_drop"),
            ([audit_event(1, "field_emitted", "assemble", field="email", candidate_id="candidate-1", evidence_refs=["evidence-1"]), audit_event(2, "field_graded", "grade", field="email", verdict="fail", reason_code="wrong_value")], {}, "grade", "wrong_value"),
        ]
        for events, ref_values, stage, cause in cases:
            with self.subTest(stage=stage):
                self.assert_cause(events, reference(**ref_values), stage, cause)

    def test_reports_trace_incomplete_instead_of_guessing(self):
        self.assert_cause([], reference(), "trace", "trace_incomplete")

    def test_structural_earliest_cause_wins_over_later_reason(self):
        events = [audit_event(1, "field_missing", "assemble", field="email", reason_code="assembly_drop")]
        self.assert_cause(
            events,
            reference(expected_source_ids=["source-1"]),
            "discover",
            "source_not_discovered",
        )

    def test_preserves_contributing_events_and_replayability(self):
        events = [
            audit_event(1, "candidate_declared", "normalize", candidate_id="candidate-1"),
            audit_event(2, "context_packed", "pack", candidate_ids=["candidate-1"]),
            audit_event(3, "decision_recorded", "judge", field="email", candidate_ids=["candidate-1"], decision={"outcome": "reject", "reason_code": "below_threshold"}),
            audit_event(4, "field_rejected", "accept", field="email", reason_code="below_threshold"),
        ]
        report = generate_report(events, reference(expected_candidate_ids=["candidate-1"]))
        gap = report["gaps"][0]
        self.assertEqual("event-3", gap["causal_event_id"])
        self.assertEqual(["event-4"], gap["contributing_event_ids"])
        self.assertTrue(gap["replayable"])

    def test_json_cli_validates_inputs_and_emits_report(self):
        events = audit_fixture.AuditLogValidationTests().valid_events()
        frozen = reference(field="profile")
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            reference_path = Path(directory) / "reference.json"
            audit_path.write_text("\n".join(json.dumps(item) for item in events) + "\n", encoding="utf-8")
            reference_path.write_text(json.dumps(frozen), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(ROOT / "scripts" / "generate_gap_attribution.py"), str(audit_path), str(reference_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual("reference-v1", report["reference_version"])
        self.assertEqual("source_not_discovered", report["gaps"][0]["primary_cause"])


if __name__ == "__main__":
    unittest.main()
