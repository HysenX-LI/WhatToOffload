#!/usr/bin/env python3
"""Validate the portable WhatToOffload JSONL audit contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable


STAGES = {
    "discover", "retrieve", "normalize", "pack", "judge", "extract",
    "repair", "accept", "assemble", "grade", "run",
}
EXECUTORS = {"code", "tool", "jev", "llm", "agent", "human"}
STATUSES = {"started", "completed", "failed", "unresolved", "skipped"}
MODEL_EXECUTORS = {"jev", "llm", "agent"}
FIELD_TERMINALS = {"field_emitted", "field_missing", "field_rejected", "field_quarantined"}
DENIED_KEYS = {
    "api_key", "authorization", "credential", "password", "raw_prompt",
    "raw_response", "raw_source", "secret",
}
SECRET_PATTERN = re.compile(r"(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|\bsk-[A-Za-z0-9_-]{12,})", re.I)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, str(key), item
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_number}: event must be a JSON object")
            continue
        value["__line__"] = line_number
        events.append(value)
    return events, errors


def validate_events(events: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    accepted: set[tuple[str, str]] = set()
    run_ids: set[str] = set()
    last_seq = -1
    emitted = missing = 0

    for index, event in enumerate(events):
        line = event.get("__line__", index + 1)
        label = f"line {line}"
        required = (
            "schema_version", "run_id", "event_id", "seq", "timestamp",
            "workflow_version", "node_id", "stage", "event_type",
            "executor", "status", "privacy",
        )
        for key in required:
            if key not in event:
                errors.append(f"{label}: missing {key}")
        if event.get("schema_version") != 1:
            errors.append(f"{label}: unsupported schema_version")
        for key in ("run_id", "event_id", "timestamp", "workflow_version", "node_id", "event_type", "privacy"):
            if key in event and not _nonempty_string(event[key]):
                errors.append(f"{label}: {key} must be a non-empty string")

        run_id = event.get("run_id")
        if _nonempty_string(run_id):
            run_ids.add(run_id)
        event_id = event.get("event_id")
        if _nonempty_string(event_id):
            if event_id in seen_ids:
                errors.append(f"{label}: duplicate event_id {event_id}")
            seen_ids.add(event_id)
        seq = event.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
            errors.append(f"{label}: seq must be a non-negative integer")
        elif seq <= last_seq:
            errors.append(f"{label}: seq must be strictly increasing")
        else:
            last_seq = seq

        if event.get("stage") not in STAGES:
            errors.append(f"{label}: unknown stage {event.get('stage')!r}")
        if event.get("executor") not in EXECUTORS:
            errors.append(f"{label}: unknown executor {event.get('executor')!r}")
        if event.get("status") not in STATUSES:
            errors.append(f"{label}: unknown status {event.get('status')!r}")
        for parent in event.get("parents", []):
            if parent not in seen_ids:
                errors.append(f"{label}: parent {parent!r} must reference an earlier event")

        for path, key, value in _walk(event):
            if key.casefold() in DENIED_KEYS:
                errors.append(f"{label}: portable log contains denied key {path}.{key}")
            if isinstance(value, str) and SECRET_PATTERN.search(value):
                errors.append(f"{label}: portable log contains a credential-like value at {path}.{key}")

        event_type = event.get("event_type")
        executor = event.get("executor")
        if event_type == "decision_recorded":
            if not event.get("candidate_ids"):
                errors.append(f"{label}: decision_recorded requires candidate_ids")
            decision = event.get("decision")
            if not isinstance(decision, dict):
                errors.append(f"{label}: decision_recorded requires decision")
            else:
                if not _nonempty_string(decision.get("outcome")):
                    errors.append(f"{label}: decision.outcome is required")
                if not _nonempty_string(decision.get("reason_code")):
                    errors.append(f"{label}: decision.reason_code is required")
                for key in ("score", "threshold"):
                    value = decision.get(key)
                    if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1):
                        errors.append(f"{label}: decision.{key} must be between 0 and 1")
        if executor in MODEL_EXECUTORS and event_type == "decision_recorded":
            for key in ("request_ref", "response_ref", "contract_version", "model"):
                if not _nonempty_string(event.get(key)):
                    errors.append(f"{label}: model decision requires {key}")

        if event_type == "context_packed":
            coverage = event.get("coverage")
            if not isinstance(coverage, dict):
                errors.append(f"{label}: context_packed requires coverage")
            else:
                values = [coverage.get(key) for key in ("eligible", "packed", "excluded")]
                if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
                    errors.append(f"{label}: coverage counts must be non-negative integers")
                elif values[1] + values[2] != values[0]:
                    errors.append(f"{label}: packed + excluded must equal eligible")

        field = event.get("field")
        candidate_id = event.get("candidate_id")
        if event_type == "field_accepted":
            if not _nonempty_string(field) or not _nonempty_string(candidate_id):
                errors.append(f"{label}: field_accepted requires field and candidate_id")
            elif not event.get("evidence_refs"):
                errors.append(f"{label}: field_accepted requires evidence_refs")
            else:
                accepted.add((field, candidate_id))
        elif event_type == "field_emitted":
            emitted += 1
            if (field, candidate_id) not in accepted:
                errors.append(f"{label}: field_emitted requires an earlier matching field_accepted")
            if not event.get("evidence_refs"):
                errors.append(f"{label}: field_emitted requires evidence_refs")
        elif event_type in {"field_missing", "field_rejected", "field_quarantined"}:
            missing += int(event_type == "field_missing")
            if not _nonempty_string(field) or not _nonempty_string(event.get("reason_code")):
                errors.append(f"{label}: {event_type} requires field and reason_code")

    if len(run_ids) > 1:
        errors.append("audit file must contain exactly one run_id")
    if events:
        if events[0].get("event_type") != "run_started":
            errors.append("first event must be run_started")
        if events[-1].get("event_type") != "run_finished":
            errors.append("last event must be run_finished")
        summary = events[-1].get("summary")
        if not isinstance(summary, dict):
            errors.append("run_finished requires summary")
        else:
            if summary.get("fields_emitted") != emitted:
                errors.append("run_finished fields_emitted does not match field_emitted events")
            if summary.get("fields_missing") != missing:
                errors.append("run_finished fields_missing does not match field_missing events")
    else:
        errors.append("audit log contains no events")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="JSONL audit log")
    args = parser.parse_args()
    events, errors = load_jsonl(args.log)
    errors.extend(validate_events(events))
    result = {"status": "valid" if not errors else "invalid", "events": len(events), "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
