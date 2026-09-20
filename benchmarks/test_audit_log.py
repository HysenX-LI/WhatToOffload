import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_audit_log import load_jsonl, validate_events


def event(seq, event_type, **values):
    base = {
        "schema_version": 1,
        "run_id": "run-1",
        "event_id": f"event-{seq}",
        "seq": seq,
        "timestamp": "2026-01-01T00:00:00Z",
        "workflow_version": "workflow-v1",
        "node_id": "node",
        "stage": "run",
        "event_type": event_type,
        "executor": "code",
        "status": "completed",
        "privacy": "metadata",
        "parents": [f"event-{seq - 1}"] if seq else [],
    }
    base.update(values)
    return base


class AuditLogValidationTests(unittest.TestCase):
    def valid_events(self):
        return [
            event(0, "run_started", status="started"),
            event(
                1,
                "field_accepted",
                stage="accept",
                field="email",
                candidate_id="candidate-1",
                evidence_refs=["evidence-1"],
            ),
            event(
                2,
                "field_emitted",
                stage="assemble",
                field="email",
                candidate_id="candidate-1",
                evidence_refs=["evidence-1"],
            ),
            event(3, "field_missing", stage="assemble", field="profile", reason_code="source_not_discovered"),
            event(4, "run_finished", summary={"fields_emitted": 1, "fields_missing": 1}),
        ]

    def test_valid_lineage(self):
        self.assertEqual([], validate_events(self.valid_events()))

    def test_emitted_field_requires_accepted_lineage(self):
        events = self.valid_events()
        events.pop(1)
        for index, item in enumerate(events):
            item["seq"] = index
            item["event_id"] = f"event-{index}"
            item["parents"] = [f"event-{index - 1}"] if index else []
        errors = validate_events(events)
        self.assertTrue(any("earlier matching field_accepted" in error for error in errors))

    def test_model_decision_requires_snapshot_references(self):
        events = self.valid_events()
        decision = event(
            1,
            "decision_recorded",
            stage="judge",
            executor="jev",
            candidate_ids=["candidate-1"],
            decision={"outcome": "reject", "score": 0.6, "threshold": 0.8, "reason_code": "below_threshold"},
        )
        events.insert(1, decision)
        for index, item in enumerate(events):
            item["seq"] = index
            item["event_id"] = f"event-{index}"
            item["parents"] = [f"event-{index - 1}"] if index else []
        errors = validate_events(events)
        self.assertTrue(any("model decision requires request_ref" in error for error in errors))

    def test_context_coverage_must_balance(self):
        events = self.valid_events()
        packed = event(1, "context_packed", stage="pack", coverage={"eligible": 8, "packed": 6, "excluded": 1})
        events.insert(1, packed)
        for index, item in enumerate(events):
            item["seq"] = index
            item["event_id"] = f"event-{index}"
            item["parents"] = [f"event-{index - 1}"] if index else []
        errors = validate_events(events)
        self.assertTrue(any("packed + excluded" in error for error in errors))

    def test_secret_like_values_are_rejected(self):
        events = self.valid_events()
        events[1]["api_key"] = "sk-examplecredential123"
        errors = validate_events(events)
        self.assertTrue(any("denied key" in error for error in errors))
        self.assertTrue(any("credential-like" in error for error in errors))

    def test_jsonl_loader_reports_bad_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            path.write_text(json.dumps(self.valid_events()[0]) + "\nnot-json\n", encoding="utf-8")
            events, errors = load_jsonl(path)
        self.assertEqual(1, len(events))
        self.assertTrue(any("invalid JSON" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
