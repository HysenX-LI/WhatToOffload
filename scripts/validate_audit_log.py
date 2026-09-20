#!/usr/bin/env python3
"""Validate the portable WhatToOffload JSONL audit contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


STAGES = {
    "run", "discover", "retrieve", "parse", "normalize", "pack",
    "judge", "repair", "accept", "assemble", "grade",
}
EXECUTORS = {"code", "tool", "jev", "llm", "agent", "human"}
STATUSES = {"started", "completed", "failed", "unresolved", "skipped"}
PRIVACY_LEVELS = {"metadata", "pseudonymous", "aggregate"}
MODEL_EXECUTORS = {"jev", "llm", "agent"}
FIELD_TERMINALS = {"field_emitted", "field_missing", "field_rejected", "field_quarantined"}
EVENT_STAGES = {
    "run_started": {"run"},
    "source_declared": {"discover"},
    "source_retrieved": {"retrieve"},
    "candidate_declared": {"parse", "normalize"},
    "evidence_declared": {"retrieve", "parse", "normalize", "repair"},
    "context_packed": {"pack"},
    "decision_recorded": {"judge"},
    "fallback_started": {"repair"},
    "evidence_supplemented": {"repair"},
    "evidence_replaced": {"repair"},
    "field_accepted": {"accept"},
    "field_rejected": {"accept"},
    "field_quarantined": {"accept"},
    "field_missing": {"accept", "assemble"},
    "field_emitted": {"assemble"},
    "field_graded": {"grade"},
    "budget_recorded": {"discover", "retrieve", "pack", "judge", "repair"},
    "run_finished": {"run"},
}
EVENT_TYPES = set(EVENT_STAGES)
ALLOWED_EVENT_KEYS = {
    "schema_version", "run_id", "event_id", "seq", "timestamp",
    "workflow_version", "node_id", "stage", "event_type", "executor",
    "status", "privacy", "parents", "subject_ref", "required_fields",
    "source_id", "source_ids", "candidate_id", "candidate_ids",
    "evidence_id", "evidence_refs", "prior_evidence_ids", "field", "fields",
    "trigger_event_id", "request_ref", "response_ref", "trace_ref",
    "contract_version", "model", "reason_code", "decision", "coverage",
    "budget", "verdict", "metrics", "summary", "__line__",
}

REASON_STAGE = {
    "source_not_discovered": "discover",
    "source_not_retrieved": "retrieve",
    "fetch_failed": "retrieve",
    "budget_exhausted": "retrieve",
    "parser_unsupported": "parse",
    "candidate_omitted": "normalize",
    "normalization_loss": "normalize",
    "candidate_overflow": "normalize",
    "context_omission": "pack",
    "batch_not_evaluated": "pack",
    "identity_context_missing": "pack",
    "above_threshold": "judge",
    "below_threshold": "judge",
    "semantic_rejection": "judge",
    "ambiguous_candidates": "judge",
    "provider_failure": "judge",
    "exception_not_routed": "repair",
    "repair_unsupported": "repair",
    "repair_rejected": "repair",
    "evidence_overwritten": "repair",
    "typed_handoff_lost": "accept",
    "assembly_drop": "assemble",
    "output_contract_failure": "assemble",
    "wrong_identity": "grade",
    "wrong_value": "grade",
    "missing_evidence": "grade",
    "reference_or_grader_gap": "grade",
    "trace_incomplete": "trace",
}
REASON_CODES = set(REASON_STAGE)

DENIED_KEYS = {
    "api_key", "authorization", "credential", "password", "raw_prompt",
    "raw_response", "raw_source", "raw_payload", "secret", "access_token",
    "refresh_token", "cookie", "email_address", "phone_number", "postal_address",
    "prompt", "response", "payload", "source_text", "content", "body",
    "name", "full_name", "email", "phone", "address", "url", "uri", "source_url",
}
SECRET_PATTERN = re.compile(
    r"(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|\b(?:sk|pk)-[A-Za-z0-9_-]{12,})",
    re.I,
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d .()-]{8,}\d)(?!\w)")
ABSOLUTE_PATH_PATTERN = re.compile(r"^(?:/|~/|[A-Za-z]:[\\/])")
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.I)
OPAQUE_REF_PATTERN = re.compile(r"^opaque:[A-Za-z0-9._-]+$")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(_nonempty_string(item) for item in value)
    )


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield path, str(key), item
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def _safe_trace_ref(value: Any) -> tuple[bool, bool]:
    if not isinstance(value, dict):
        return False, False
    if set(value) != {"ref", "sha256"}:
        return False, isinstance(value.get("sha256"), str) and bool(HASH_PATTERN.fullmatch(value["sha256"]))
    ref = value.get("ref")
    digest = value.get("sha256")
    has_hash = isinstance(digest, str) and bool(HASH_PATTERN.fullmatch(digest))
    if not _nonempty_string(ref):
        return False, has_hash
    if OPAQUE_REF_PATTERN.fullmatch(ref):
        return True, has_hash
    if ABSOLUTE_PATH_PATTERN.search(ref) or "\\" in ref or "://" in ref:
        return False, has_hash
    path = PurePosixPath(ref)
    safe = not path.is_absolute() and ".." not in path.parts and "." not in path.parts
    return safe, has_hash


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
    run_ids: set[str] = set()
    source_events: dict[str, str] = {}
    candidate_events: dict[str, str] = {}
    evidence_events: dict[str, str] = {}
    evidence_candidates: dict[str, set[str]] = {}
    packed_candidates: set[str] = set()
    accepted: dict[tuple[str, str], set[str]] = {}
    field_terminals: dict[str, list[str]] = {}
    required_fields: set[str] = set()
    last_seq = -1
    counts = {
        "sources_declared": 0,
        "candidates_declared": 0,
        "evidence_declared": 0,
        "decisions": 0,
        "budget_events": 0,
        "fields_emitted": 0,
        "fields_missing": 0,
        "fields_rejected": 0,
        "fields_quarantined": 0,
    }

    for index, event in enumerate(events):
        line = event.get("__line__", index + 1)
        label = f"line {line}"
        required = (
            "schema_version", "run_id", "event_id", "seq", "timestamp",
            "workflow_version", "node_id", "stage", "event_type",
            "executor", "status", "privacy", "parents",
        )
        for key in required:
            if key not in event:
                errors.append(f"{label}: missing {key}")
        for key in sorted(set(event) - ALLOWED_EVENT_KEYS):
            errors.append(f"{label}: unknown event property {key!r}")
        if event.get("schema_version") != 1:
            errors.append(f"{label}: unsupported schema_version")
        for key in ("run_id", "event_id", "timestamp", "workflow_version", "node_id", "event_type"):
            if key in event and not _nonempty_string(event[key]):
                errors.append(f"{label}: {key} must be a non-empty string")

        run_id = event.get("run_id")
        if _nonempty_string(run_id):
            run_ids.add(run_id)
        event_id = event.get("event_id")
        prior_event_ids = set(seen_ids)
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

        stage = event.get("stage")
        event_type = event.get("event_type")
        if stage not in STAGES:
            errors.append(f"{label}: unknown stage {stage!r}")
        if event_type not in EVENT_TYPES:
            errors.append(f"{label}: unknown event_type {event_type!r}")
        elif stage not in EVENT_STAGES[event_type]:
            errors.append(f"{label}: {event_type} cannot use stage {stage!r}")
        if event.get("executor") not in EXECUTORS:
            errors.append(f"{label}: unknown executor {event.get('executor')!r}")
        if event.get("status") not in STATUSES:
            errors.append(f"{label}: unknown status {event.get('status')!r}")
        if event.get("privacy") not in PRIVACY_LEVELS:
            errors.append(f"{label}: unknown privacy {event.get('privacy')!r}")
        subject_ref = event.get("subject_ref")
        if subject_ref is not None and (
            not isinstance(subject_ref, str)
            or not subject_ref.startswith("sha256:")
            or not HASH_PATTERN.fullmatch(subject_ref[7:])
        ):
            errors.append(f"{label}: subject_ref must be a sha256 reference")
        parents = event.get("parents", [])
        if not _string_list(parents):
            errors.append(f"{label}: parents must be an array of event IDs")
            parents = []
        for parent in parents:
            if parent not in prior_event_ids:
                errors.append(f"{label}: parent {parent!r} must reference an earlier event")

        for path, key, value in _walk(event):
            if key.startswith("__"):
                continue
            if key.casefold() in DENIED_KEYS:
                errors.append(f"{label}: portable log contains denied key {path}.{key}")
            if isinstance(value, str):
                if SECRET_PATTERN.search(value):
                    errors.append(f"{label}: portable log contains a credential-like value at {path}.{key}")
                if EMAIL_PATTERN.search(value) or PHONE_PATTERN.search(value):
                    errors.append(f"{label}: portable log contains a personal-data-like value at {path}.{key}")
                if ABSOLUTE_PATH_PATTERN.search(value):
                    errors.append(f"{label}: portable log contains an absolute path at {path}.{key}")

        reason_codes = []
        if _nonempty_string(event.get("reason_code")):
            reason_codes.append(event["reason_code"])
        decision = event.get("decision")
        if isinstance(decision, dict) and _nonempty_string(decision.get("reason_code")):
            reason_codes.append(decision["reason_code"])
        for reason_code in reason_codes:
            if reason_code not in REASON_CODES:
                errors.append(f"{label}: unknown reason_code {reason_code!r}")

        if event_type in FIELD_TERMINALS | {"field_accepted", "field_graded"}:
            field = event.get("field")
            if _nonempty_string(field) and field not in required_fields:
                errors.append(f"{label}: field {field!r} was not declared in required_fields")

        if event_type == "run_started":
            fields = event.get("required_fields")
            if not _string_list(fields, nonempty=True) or len(set(fields)) != len(fields):
                errors.append(f"{label}: run_started requires unique required_fields")
            else:
                required_fields = set(fields)

        elif event_type == "source_declared":
            source_id = event.get("source_id")
            if not _nonempty_string(source_id):
                errors.append(f"{label}: source_declared requires source_id")
            elif source_id in source_events:
                errors.append(f"{label}: duplicate source_id {source_id}")
            else:
                source_events[source_id] = event_id
                counts["sources_declared"] += 1

        elif event_type == "source_retrieved":
            source_id = event.get("source_id")
            if source_id not in source_events:
                errors.append(f"{label}: source_retrieved references undeclared source {source_id!r}")

        elif event_type == "candidate_declared":
            candidate_id = event.get("candidate_id")
            source_ids = event.get("source_ids")
            if not _nonempty_string(candidate_id):
                errors.append(f"{label}: candidate_declared requires candidate_id")
            elif candidate_id in candidate_events:
                errors.append(f"{label}: duplicate candidate_id {candidate_id}")
            if not _string_list(source_ids, nonempty=True):
                errors.append(f"{label}: candidate_declared requires source_ids")
                source_ids = []
            for source_id in source_ids:
                if source_id not in source_events:
                    errors.append(f"{label}: candidate_declared references undeclared source {source_id!r}")
            if _nonempty_string(candidate_id) and candidate_id not in candidate_events:
                candidate_events[candidate_id] = event_id
                counts["candidates_declared"] += 1

        elif event_type == "evidence_declared":
            evidence_id = event.get("evidence_id")
            candidate_ids = event.get("candidate_ids")
            source_ids = event.get("source_ids")
            if not _nonempty_string(evidence_id):
                errors.append(f"{label}: evidence_declared requires evidence_id")
            elif evidence_id in evidence_events:
                errors.append(f"{label}: duplicate evidence_id {evidence_id}")
            if not _string_list(candidate_ids, nonempty=True):
                errors.append(f"{label}: evidence_declared requires candidate_ids")
                candidate_ids = []
            if not _string_list(source_ids, nonempty=True):
                errors.append(f"{label}: evidence_declared requires source_ids")
                source_ids = []
            for candidate_id in candidate_ids:
                if candidate_id not in candidate_events:
                    errors.append(f"{label}: evidence_declared references undeclared candidate {candidate_id!r}")
            for source_id in source_ids:
                if source_id not in source_events:
                    errors.append(f"{label}: evidence_declared references undeclared source {source_id!r}")
            if _nonempty_string(evidence_id) and evidence_id not in evidence_events:
                evidence_events[evidence_id] = event_id
                evidence_candidates[evidence_id] = set(candidate_ids)
                counts["evidence_declared"] += 1
            if "trace_ref" in event:
                safe, hashed = _safe_trace_ref(event["trace_ref"])
                if not safe:
                    errors.append(f"{label}: trace_ref.ref must be a safe relative or opaque reference")
                if not hashed:
                    errors.append(f"{label}: trace_ref.sha256 must be a 64-character hexadecimal hash")

        elif event_type == "context_packed":
            candidate_ids = event.get("candidate_ids")
            if not _string_list(candidate_ids):
                errors.append(f"{label}: context_packed candidate_ids must be an array")
                candidate_ids = []
            for candidate_id in candidate_ids:
                if candidate_id not in candidate_events:
                    errors.append(f"{label}: context_packed references undeclared candidate {candidate_id!r}")
                else:
                    packed_candidates.add(candidate_id)
            coverage = event.get("coverage")
            if not isinstance(coverage, dict):
                errors.append(f"{label}: context_packed requires coverage")
            else:
                keys = ("eligible", "packed", "excluded", "unevaluated")
                values = [coverage.get(key) for key in keys]
                if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
                    errors.append(f"{label}: coverage counts must be non-negative integers")
                elif values[1] + values[2] + values[3] != values[0]:
                    errors.append(f"{label}: packed + excluded + unevaluated must equal eligible")
                elif values[1] != len(candidate_ids):
                    errors.append(f"{label}: coverage.packed must equal candidate_ids length")

        elif event_type == "decision_recorded":
            counts["decisions"] += 1
            candidate_ids = event.get("candidate_ids")
            if not _string_list(candidate_ids, nonempty=True):
                errors.append(f"{label}: decision_recorded requires candidate_ids")
                candidate_ids = []
            for candidate_id in candidate_ids:
                if candidate_id not in candidate_events:
                    errors.append(f"{label}: decision_recorded references undeclared candidate {candidate_id!r}")
                elif candidate_id not in packed_candidates:
                    errors.append(f"{label}: decision_recorded references candidate {candidate_id!r} that was not packed")
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
            if event.get("executor") in MODEL_EXECUTORS:
                for key in ("request_ref", "response_ref"):
                    safe, hashed = _safe_trace_ref(event.get(key))
                    if not safe:
                        errors.append(f"{label}: {key}.ref must be a safe relative or opaque reference")
                    if not hashed:
                        errors.append(f"{label}: {key}.sha256 must be a 64-character hexadecimal hash")
                for key in ("contract_version", "model"):
                    if not _nonempty_string(event.get(key)):
                        errors.append(f"{label}: model decision requires {key}")

        elif event_type == "fallback_started":
            fields = event.get("fields")
            trigger = event.get("trigger_event_id")
            if not _string_list(fields, nonempty=True):
                errors.append(f"{label}: fallback_started requires fields scope")
                fields = []
            for field in fields:
                if field not in required_fields:
                    errors.append(f"{label}: fallback scope references undeclared field {field!r}")
            if not _nonempty_string(event.get("reason_code")):
                errors.append(f"{label}: fallback_started requires reason_code")
            if trigger not in parents:
                errors.append(f"{label}: fallback_started trigger_event_id must be an explicit parent")

        elif event_type in {"evidence_supplemented", "evidence_replaced"}:
            evidence_id = event.get("evidence_id")
            prior_ids = event.get("prior_evidence_ids")
            fields = event.get("fields")
            candidate_ids = event.get("candidate_ids")
            if evidence_id not in evidence_events:
                errors.append(f"{label}: {event_type} references undeclared evidence {evidence_id!r}")
            if not _string_list(prior_ids, nonempty=True):
                errors.append(f"{label}: {event_type} requires prior_evidence_ids")
                prior_ids = []
            if not _string_list(fields, nonempty=True):
                errors.append(f"{label}: {event_type} requires fields scope")
                fields = []
            if not _string_list(candidate_ids, nonempty=True):
                errors.append(f"{label}: {event_type} requires candidate_ids scope")
                candidate_ids = []
            if not _nonempty_string(event.get("reason_code")):
                errors.append(f"{label}: {event_type} requires reason_code")
            for field in fields:
                if field not in required_fields:
                    errors.append(f"{label}: {event_type} scope references undeclared field {field!r}")
            for candidate_id in candidate_ids:
                if candidate_id not in candidate_events:
                    errors.append(f"{label}: {event_type} references undeclared candidate {candidate_id!r}")
                elif evidence_id in evidence_candidates and candidate_id not in evidence_candidates[evidence_id]:
                    errors.append(f"{label}: evidence {evidence_id!r} is not linked to candidate {candidate_id!r}")
            for prior_id in prior_ids:
                if prior_id not in evidence_events:
                    errors.append(f"{label}: {event_type} references undeclared evidence {prior_id!r}")
                else:
                    for candidate_id in candidate_ids:
                        if candidate_id not in evidence_candidates[prior_id]:
                            errors.append(f"{label}: prior evidence {prior_id!r} is not linked to candidate {candidate_id!r}")
            required_parents = {evidence_events[item] for item in [evidence_id] + prior_ids if item in evidence_events}
            if not required_parents.issubset(set(parents)):
                errors.append(f"{label}: {event_type} requires declaration events as explicit parents")

        elif event_type in {"field_accepted", "field_emitted"}:
            field = event.get("field")
            candidate_id = event.get("candidate_id")
            refs = event.get("evidence_refs")
            if not _nonempty_string(field) or not _nonempty_string(candidate_id):
                errors.append(f"{label}: {event_type} requires field and candidate_id")
            if candidate_id not in candidate_events:
                errors.append(f"{label}: {event_type} references undeclared candidate {candidate_id!r}")
            if not _string_list(refs, nonempty=True):
                errors.append(f"{label}: {event_type} requires evidence_refs")
                refs = []
            for evidence_id in refs:
                if evidence_id not in evidence_events:
                    errors.append(f"{label}: {event_type} references undeclared evidence {evidence_id!r}")
                elif candidate_id not in evidence_candidates[evidence_id]:
                    errors.append(f"{label}: evidence {evidence_id!r} is not linked to candidate {candidate_id!r}")
            key = (field, candidate_id)
            if event_type == "field_accepted":
                accepted[key] = set(refs)
            else:
                counts["fields_emitted"] += 1
                if key not in accepted:
                    errors.append(f"{label}: field_emitted requires an earlier matching field_accepted")
                elif not accepted[key].issubset(set(refs)):
                    errors.append(f"{label}: field_emitted lost accepted evidence lineage")

        elif event_type in {"field_missing", "field_rejected", "field_quarantined"}:
            field = event.get("field")
            if not _nonempty_string(field) or not _nonempty_string(event.get("reason_code")):
                errors.append(f"{label}: {event_type} requires field and reason_code")
            counts[event_type.replace("field_", "fields_")] += 1

        elif event_type == "field_graded":
            if not _nonempty_string(event.get("field")) or event.get("verdict") not in {"pass", "fail"}:
                errors.append(f"{label}: field_graded requires field and pass/fail verdict")
            if event.get("verdict") == "fail" and not _nonempty_string(event.get("reason_code")):
                errors.append(f"{label}: failed field_graded requires reason_code")

        elif event_type == "budget_recorded":
            counts["budget_events"] += 1
            budget = event.get("budget")
            if not isinstance(budget, dict):
                errors.append(f"{label}: budget_recorded requires budget")
            else:
                if budget.get("unit") not in {"pages", "calls", "time_ms", "tokens", "cost_usd", "retries"}:
                    errors.append(f"{label}: budget.unit is invalid")
                for key in ("limit", "used"):
                    value = budget.get(key)
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                        errors.append(f"{label}: budget.{key} must be a non-negative number")
                if not isinstance(budget.get("exhausted"), bool):
                    errors.append(f"{label}: budget.exhausted must be boolean")
                elif budget["exhausted"] and event.get("reason_code") != "budget_exhausted":
                    errors.append(f"{label}: exhausted budget requires budget_exhausted reason_code")

        if event_type in FIELD_TERMINALS and _nonempty_string(event.get("field")):
            field_terminals.setdefault(event["field"], []).append(event_type)

    if len(run_ids) != 1 and events:
        errors.append("audit file must contain exactly one run_id")
    if events:
        if events[0].get("event_type") != "run_started":
            errors.append("first event must be run_started")
        if events[-1].get("event_type") != "run_finished":
            errors.append("last event must be run_finished")
        for field in sorted(required_fields):
            terminals = field_terminals.get(field, [])
            if not terminals:
                errors.append(f"required field {field!r} has no terminal event")
            elif len(terminals) > 1:
                errors.append(f"required field {field!r} has conflicting terminal events")
        summary = events[-1].get("summary")
        if not isinstance(summary, dict):
            errors.append("run_finished requires summary")
        else:
            for key, actual in counts.items():
                if summary.get(key) != actual:
                    errors.append(f"run_finished summary {key} does not match events")
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
