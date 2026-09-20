import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_audit_log import load_jsonl, validate_events


HASH = "a" * 64


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


def reindex(events):
    for index, item in enumerate(events):
        item["seq"] = index
        item["event_id"] = f"event-{index}"
        item["parents"] = [f"event-{index - 1}"] if index else []


class AuditLogValidationTests(unittest.TestCase):
    def valid_events(self):
        return [
            event(0, "run_started", status="started", required_fields=["email", "profile"]),
            event(1, "source_declared", stage="discover", source_id="source-1"),
            event(2, "source_retrieved", stage="retrieve", source_id="source-1"),
            event(3, "candidate_declared", stage="normalize", candidate_id="candidate-1", source_ids=["source-1"]),
            event(4, "evidence_declared", stage="normalize", evidence_id="evidence-1", candidate_ids=["candidate-1"], source_ids=["source-1"]),
            event(5, "context_packed", stage="pack", candidate_ids=["candidate-1"], coverage={"eligible": 1, "packed": 1, "excluded": 0, "unevaluated": 0}),
            event(
                6,
                "decision_recorded",
                stage="judge",
                executor="jev",
                field="email",
                candidate_ids=["candidate-1"],
                request_ref={"ref": "local-traces/request-6.json", "sha256": HASH},
                response_ref={"ref": "opaque:response-6", "sha256": HASH},
                contract_version="email-v1",
                model="provider/model-version",
                decision={"outcome": "accept", "score": 0.9, "threshold": 0.8, "reason_code": "above_threshold"},
            ),
            event(7, "field_accepted", stage="accept", field="email", candidate_id="candidate-1", evidence_refs=["evidence-1"]),
            event(8, "field_emitted", stage="assemble", field="email", candidate_id="candidate-1", evidence_refs=["evidence-1"]),
            event(9, "field_missing", stage="assemble", field="profile", reason_code="source_not_discovered"),
            event(
                10,
                "run_finished",
                summary={
                    "sources_declared": 1,
                    "candidates_declared": 1,
                    "evidence_declared": 1,
                    "decisions": 1,
                    "budget_events": 0,
                    "fields_emitted": 1,
                    "fields_missing": 1,
                    "fields_rejected": 0,
                    "fields_quarantined": 0,
                },
            ),
        ]

    def test_valid_complete_lineage(self):
        self.assertEqual([], validate_events(self.valid_events()))

    def test_unknown_event_type_is_rejected(self):
        events = self.valid_events()
        events.insert(-1, event(10, "made_up_event"))
        reindex(events)
        errors = validate_events(events)
        self.assertTrue(any("unknown event_type" in error for error in errors))

    def test_unknown_event_property_is_rejected(self):
        events = self.valid_events()
        events[1]["free_form_note"] = "not in the portable contract"
        errors = validate_events(events)
        self.assertTrue(any("unknown event property" in error for error in errors))

    def test_accepted_field_rejects_invented_candidate_and_evidence(self):
        events = self.valid_events()
        accepted = next(item for item in events if item["event_type"] == "field_accepted")
        accepted["candidate_id"] = "candidate-invented"
        accepted["evidence_refs"] = ["evidence-invented"]
        errors = validate_events(events)
        self.assertTrue(any("undeclared candidate" in error for error in errors))
        self.assertTrue(any("undeclared evidence" in error for error in errors))

    def test_model_trace_reference_requires_hash_and_safe_reference(self):
        events = self.valid_events()
        decision = next(item for item in events if item["event_type"] == "decision_recorded")
        decision["request_ref"] = {"ref": "/Users/person/private.json"}
        errors = validate_events(events)
        self.assertTrue(any("request_ref.sha256" in error for error in errors))
        self.assertTrue(any("request_ref.ref must be a safe" in error for error in errors))

    def test_required_field_must_have_one_terminal_event(self):
        events = [item for item in self.valid_events() if item.get("field") != "profile"]
        reindex(events)
        events[-1]["summary"]["fields_missing"] = 0
        errors = validate_events(events)
        self.assertTrue(any("required field 'profile' has no terminal event" in error for error in errors))

    def test_field_events_must_reference_a_declared_required_field(self):
        events = self.valid_events()
        emitted = next(item for item in events if item["event_type"] == "field_emitted")
        emitted["field"] = "invented_field"
        errors = validate_events(events)
        self.assertTrue(any("was not declared in required_fields" in error for error in errors))

    def test_evidence_replacement_requires_declared_lineage_and_explicit_parents(self):
        events = self.valid_events()
        replacement = event(5, "evidence_declared", stage="repair", evidence_id="evidence-2", candidate_ids=["candidate-1"], source_ids=["source-1"], fields=["email"])
        replaced = event(6, "evidence_replaced", stage="repair", evidence_id="evidence-2", prior_evidence_ids=["evidence-1"], candidate_ids=["candidate-1"], fields=["email"], reason_code="evidence_overwritten", parents=[])
        events[5:5] = [replacement, replaced]
        reindex(events)
        replaced = next(item for item in events if item["event_type"] == "evidence_replaced")
        replaced["parents"] = []
        events[-1]["summary"]["evidence_declared"] = 2
        errors = validate_events(events)
        self.assertTrue(any("explicit parents" in error for error in errors))

    def test_explicit_evidence_replacement_lineage_is_valid(self):
        events = self.valid_events()
        events[5:5] = [
            event(5, "evidence_declared", stage="repair", evidence_id="evidence-2", candidate_ids=["candidate-1"], source_ids=["source-1"], fields=["email"]),
            event(6, "evidence_replaced", stage="repair", evidence_id="evidence-2", prior_evidence_ids=["evidence-1"], candidate_ids=["candidate-1"], fields=["email"], reason_code="evidence_overwritten"),
        ]
        reindex(events)
        replaced = next(item for item in events if item["event_type"] == "evidence_replaced")
        replaced["parents"] = ["event-4", "event-5"]
        events[-1]["summary"]["evidence_declared"] = 2
        self.assertEqual([], validate_events(events))

    def test_fallback_must_be_scoped_to_declared_fields_and_trigger_parent(self):
        events = self.valid_events()
        events.insert(-1, event(10, "fallback_started", stage="repair", fields=["invented"], trigger_event_id="event-6", reason_code="exception_not_routed", parents=[]))
        reindex(events)
        fallback = next(item for item in events if item["event_type"] == "fallback_started")
        fallback["trigger_event_id"] = "event-6"
        fallback["parents"] = []
        errors = validate_events(events)
        self.assertTrue(any("fallback scope references undeclared field" in error for error in errors))
        self.assertTrue(any("trigger_event_id must be an explicit parent" in error for error in errors))

    def test_context_coverage_and_summary_counts_must_balance(self):
        events = self.valid_events()
        packed = next(item for item in events if item["event_type"] == "context_packed")
        packed["coverage"]["unevaluated"] = 1
        events[-1]["summary"]["decisions"] = 9
        errors = validate_events(events)
        self.assertTrue(any("packed + excluded + unevaluated" in error for error in errors))
        self.assertTrue(any("summary decisions" in error for error in errors))

    def test_privacy_and_sensitive_payloads_are_rejected(self):
        events = self.valid_events()
        events[1]["privacy"] = "raw"
        events[1]["raw_prompt"] = "private payload"
        events[1]["contact"] = "person@example.com"
        errors = validate_events(events)
        self.assertTrue(any("unknown privacy" in error for error in errors))
        self.assertTrue(any("denied key" in error for error in errors))
        self.assertTrue(any("personal-data-like" in error for error in errors))

    def test_jsonl_loader_reports_bad_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            path.write_text(json.dumps(self.valid_events()[0]) + "\nnot-json\n", encoding="utf-8")
            events, errors = load_jsonl(path)
        self.assertEqual(1, len(events))
        self.assertTrue(any("invalid JSON" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
