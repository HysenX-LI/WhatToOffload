#!/usr/bin/env python3
"""Generate deterministic field-level gap attribution from a validated audit log."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from scripts.validate_audit_log import REASON_STAGE, load_jsonl, validate_events
except ModuleNotFoundError:  # Direct execution from scripts/.
    from validate_audit_log import REASON_STAGE, load_jsonl, validate_events


STAGE_ORDER = {
    "discover": 0,
    "retrieve": 1,
    "parse": 2,
    "normalize": 3,
    "pack": 4,
    "judge": 5,
    "repair": 6,
    "accept": 7,
    "assemble": 8,
    "grade": 9,
    "trace": 10,
}
RECOMMENDED_BOUNDARY = {
    "discover": "source-discovery",
    "retrieve": "retrieval-policy",
    "parse": "parser",
    "normalize": "candidate-normalization",
    "pack": "context-packing",
    "judge": "semantic-decision",
    "repair": "fallback-and-evidence-merge",
    "accept": "typed-handoff",
    "assemble": "output-assembly",
    "grade": "reference-or-grader",
    "trace": "audit-instrumentation",
}
HASHED_SUBJECT = re.compile(r"^sha256:[0-9a-f]{64}$", re.I)


def load_reference(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("frozen reference must be a JSON object")
    return value


def validate_reference(reference: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in sorted(set(reference) - {"schema_version", "reference_version", "fields"}):
        errors.append(f"reference: unknown property {key!r}")
    if reference.get("schema_version") != 1:
        errors.append("reference: unsupported schema_version")
    if not isinstance(reference.get("reference_version"), str) or not reference["reference_version"].strip():
        errors.append("reference: reference_version is required")
    fields = reference.get("fields")
    if not isinstance(fields, list) or not fields:
        return errors + ["reference: fields must be a non-empty array"]
    seen: set[tuple[str, str]] = set()
    for index, field in enumerate(fields):
        label = f"reference field {index}"
        if not isinstance(field, dict):
            errors.append(f"{label}: must be an object")
            continue
        allowed = {
            "subject_ref", "field", "expected_status", "expected_source_ids",
            "expected_candidate_ids", "expected_evidence_ids", "expected_value_hash",
        }
        for key in sorted(set(field) - allowed):
            errors.append(f"{label}: unknown property {key!r}")
        subject_ref = field.get("subject_ref")
        name = field.get("field")
        if not isinstance(subject_ref, str) or not HASHED_SUBJECT.fullmatch(subject_ref):
            errors.append(f"{label}: subject_ref must be a sha256 reference")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{label}: field is required")
        elif (subject_ref, name) in seen:
            errors.append(f"{label}: duplicate subject_ref and field")
        else:
            seen.add((subject_ref, name))
        if field.get("expected_status") not in {"available", "missing", "not_applicable"}:
            errors.append(f"{label}: expected_status is invalid")
        for key in ("expected_source_ids", "expected_candidate_ids", "expected_evidence_ids"):
            value = field.get(key, [])
            if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
                errors.append(f"{label}: {key} must be an array of IDs")
            elif len(value) != len(set(value)):
                errors.append(f"{label}: {key} must contain unique IDs")
        value_hash = field.get("expected_value_hash")
        if value_hash is not None and (not isinstance(value_hash, str) or not HASHED_SUBJECT.fullmatch(value_hash)):
            errors.append(f"{label}: expected_value_hash must be a sha256 reference")
    return errors


def _event_reason(event: dict[str, Any]) -> str | None:
    reason = event.get("reason_code")
    if isinstance(reason, str):
        return reason
    decision = event.get("decision")
    if isinstance(decision, dict) and isinstance(decision.get("reason_code"), str):
        return decision["reason_code"]
    return None


def _relevant(event: dict[str, Any], field: dict[str, Any]) -> bool:
    if event.get("subject_ref") not in (None, field["subject_ref"]):
        return False
    name = field["field"]
    if event.get("field") == name or name in event.get("fields", []):
        return True
    relationships = (
        ("source_id", "source_ids", "expected_source_ids"),
        ("candidate_id", "candidate_ids", "expected_candidate_ids"),
        ("evidence_id", "evidence_refs", "expected_evidence_ids"),
    )
    for singular, plural, expected_key in relationships:
        expected = set(field.get(expected_key, []))
        if not expected:
            continue
        actual = set(event.get(plural, []))
        if isinstance(event.get(singular), str):
            actual.add(event[singular])
        if expected & actual:
            return True
    return False


def _synthetic_cause(events: list[dict[str, Any]], field: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None] | None:
    sources = set(field.get("expected_source_ids", []))
    candidates = set(field.get("expected_candidate_ids", []))
    declared_sources = {event.get("source_id") for event in events if event.get("event_type") == "source_declared"}
    retrieved_sources = {event.get("source_id") for event in events if event.get("event_type") == "source_retrieved" and event.get("status") == "completed"}
    declared_candidates = {event.get("candidate_id") for event in events if event.get("event_type") == "candidate_declared"}
    packed_candidates = {
        candidate
        for event in events if event.get("event_type") == "context_packed"
        for candidate in event.get("candidate_ids", [])
    }
    relevant = [event for event in events if _relevant(event, field)]
    terminal = next((event for event in relevant if event.get("event_type", "").startswith("field_")), None)
    if sources and not sources.issubset(declared_sources):
        return "discover", "source_not_discovered", terminal
    if sources and not sources.issubset(retrieved_sources):
        declaration = next((event for event in relevant if event.get("event_type") == "source_declared"), terminal)
        return "retrieve", "source_not_retrieved", declaration
    if candidates and not candidates.issubset(declared_candidates):
        return "normalize", "candidate_omitted", terminal
    if candidates and not candidates.issubset(packed_candidates):
        declaration = next((event for event in relevant if event.get("event_type") == "candidate_declared"), terminal)
        return "pack", "context_omission", declaration
    accepted = next((event for event in relevant if event.get("event_type") == "field_accepted"), None)
    emitted = next((event for event in relevant if event.get("event_type") == "field_emitted"), None)
    if accepted and not emitted:
        return "assemble", "assembly_drop", accepted
    return None


def _attribute(events: list[dict[str, Any]], field: dict[str, Any]) -> dict[str, Any] | None:
    if field.get("expected_status") != "available":
        return None
    relevant = [event for event in events if _relevant(event, field)]
    emitted = any(event.get("event_type") == "field_emitted" for event in relevant)
    graded_fail = any(event.get("event_type") == "field_graded" and event.get("verdict") == "fail" for event in relevant)
    if emitted and not graded_fail:
        return None
    reasoned = []
    for event in relevant:
        reason = _event_reason(event)
        if reason in REASON_STAGE and reason not in {"above_threshold", "trace_incomplete"}:
            stage = event.get("stage") if reason == "budget_exhausted" else REASON_STAGE[reason]
            reasoned.append((stage, reason, event))
    inferred = _synthetic_cause(events, field)
    explicit_stage = min((STAGE_ORDER[item[0]] for item in reasoned), default=None)
    if inferred is not None and (explicit_stage is None or STAGE_ORDER[inferred[0]] < explicit_stage):
        reasoned.append(inferred)
    if reasoned:
        reasoned.sort(key=lambda item: (STAGE_ORDER[item[0]], (item[2] or {}).get("seq", 0)))
        stage, cause, causal = reasoned[0]
    else:
        stage, cause, causal = "trace", "trace_incomplete", None
    causal_id = causal.get("event_id") if causal else None
    contributing = [
        event["event_id"]
        for event in relevant
        if event.get("event_id") != causal_id
        and (_event_reason(event) is not None or event.get("event_type") in {"field_accepted", "field_emitted", "field_graded"})
    ]
    return {
        "subject_ref": field["subject_ref"],
        "field": field["field"],
        "expected_status": field["expected_status"],
        "observed_status": "emitted_but_failed" if emitted else "missing",
        "primary_stage": stage,
        "primary_cause": cause,
        "causal_event_id": causal_id,
        "contributing_event_ids": contributing,
        "recommended_boundary": RECOMMENDED_BOUNDARY[stage],
        "replayable": causal is not None and stage in {"pack", "judge", "repair", "accept", "assemble", "grade"},
    }


def generate_report(events: list[dict[str, Any]], reference: dict[str, Any]) -> dict[str, Any]:
    workflow_version = next((event.get("workflow_version") for event in events if event.get("workflow_version")), "unknown")
    run_id = next((event.get("run_id") for event in events if event.get("run_id")), "unknown")
    gaps = []
    for field in reference.get("fields", []):
        gap = _attribute(events, field)
        if gap is not None:
            gaps.append(gap)
    by_cause = Counter(gap["primary_cause"] for gap in gaps)
    return {
        "schema_version": 1,
        "run_id": run_id,
        "workflow_version": workflow_version,
        "reference_version": reference.get("reference_version", "unknown"),
        "summary": {
            "evaluated_fields": len(reference.get("fields", [])),
            "gaps": len(gaps),
            "by_primary_cause": dict(sorted(by_cause.items())),
        },
        "gaps": gaps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit_log", type=Path, help="validated workflow audit JSONL")
    parser.add_argument("frozen_reference", type=Path, help="frozen field reference JSON")
    args = parser.parse_args()
    events, errors = load_jsonl(args.audit_log)
    errors.extend(validate_events(events))
    try:
        reference = load_reference(args.frozen_reference)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(f"reference: {exc}")
        reference = {}
    errors.extend(validate_reference(reference))
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(generate_report(events, reference), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
