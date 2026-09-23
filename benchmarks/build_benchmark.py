#!/usr/bin/env python3
"""Summarize sanitized implementation-build experiment records."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence


REQUIRED = {
    "run_id",
    "arm",
    "status",
    "wall_ms",
    "tool_calls",
    "test_commands",
    "quality_pass",
    "budget_compliant",
}
OPTIONAL_NUMERIC = {"input_tokens", "repeated_context_bytes"}
STATUSES = {"completed", "needs_reanalysis", "failed"}


def validate_record(record: Any) -> list[str]:
    errors = []
    if not isinstance(record, Mapping):
        return ["record must be an object"]
    missing = sorted(REQUIRED - set(record))
    extra = sorted(set(record) - REQUIRED - OPTIONAL_NUMERIC)
    if missing:
        errors.append("missing fields: " + ", ".join(missing))
    if extra:
        errors.append("unknown fields: " + ", ".join(extra))
    for key in ("run_id", "arm"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append(f"{key} must be a non-empty string")
    if record.get("status") not in STATUSES:
        errors.append("status is unsupported")
    for key in ("wall_ms", "tool_calls", "test_commands"):
        value = record.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{key} must be a non-negative integer")
    for key in ("quality_pass", "budget_compliant"):
        if not isinstance(record.get(key), bool):
            errors.append(f"{key} must be boolean")
    for key in OPTIONAL_NUMERIC:
        value = record.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            errors.append(f"{key} must be null or a non-negative integer")
    return errors


def _percentile(values: Iterable[int], percentile: float) -> Optional[int]:
    ordered = sorted(values)
    if not ordered:
        return None
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _optional_median(records: Sequence[Mapping[str, Any]], key: str) -> Optional[float]:
    values = [record[key] for record in records if isinstance(record.get(key), int)]
    return statistics.median(values) if values else None


def summarize(records: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    by_arm = {}
    for record in records:
        by_arm.setdefault(record["arm"], []).append(record)
    arms = {}
    for arm, arm_records in sorted(by_arm.items()):
        count = len(arm_records)
        arms[arm] = {
            "runs": count,
            "completion_rate": sum(record["status"] == "completed" for record in arm_records) / count,
            "quality_pass_rate": sum(record["quality_pass"] for record in arm_records) / count,
            "budget_compliance_rate": sum(record["budget_compliant"] for record in arm_records) / count,
            "median_wall_ms": statistics.median(record["wall_ms"] for record in arm_records),
            "p90_wall_ms": _percentile((record["wall_ms"] for record in arm_records), 0.90),
            "median_tool_calls": statistics.median(record["tool_calls"] for record in arm_records),
            "median_test_commands": statistics.median(record["test_commands"] for record in arm_records),
            "median_input_tokens": _optional_median(arm_records, "input_tokens"),
            "median_repeated_context_bytes": _optional_median(arm_records, "repeated_context_bytes"),
        }
    return {"run_count": len(records), "arms": arms}


def load_records(path: Path) -> Sequence[Mapping[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    value = json.loads(text)
    if not isinstance(value, list):
        raise ValueError("JSON input must be an array")
    return value


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path)
    args = parser.parse_args(argv)
    try:
        records = load_records(args.records)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, indent=2))
        return 1
    errors = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_record(record))
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps(summarize(records), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
