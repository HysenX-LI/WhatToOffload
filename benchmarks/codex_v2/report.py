"""Codex measurements and quality from immutable records, never model estimates."""
import json
from pathlib import Path
from benchmarks.public_v1.report import aggregate as quality_aggregate, ratio, render as quality_render


def usage(calls):
    result = {"codex_calls": len(calls), "tool_calls": sum(c.get("tool_calls", 0) for c in calls), "billing_cost": None,
              "failed_calls": sum(c.get("status") != "completed" for c in calls),
              "transport_reconnections": sum(c.get("transport_reconnections", 0) for c in calls),
              "tool_count_basis": "unique CLI-reported tool items; unreported internal invocations unknown"}
    for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
        known = [c[key] for c in calls if c.get(key) is not None]
        result[key] = sum(known) if len(known) == len(calls) else None
        result[key + "_known_subtotal"] = sum(known)
        result[key + "_measured_calls"] = len(known)
    return result


def aggregate(records):
    stats = quality_aggregate(records)
    for arm, entry in stats.items():
        rows = [r for r in records if r["arm"] == arm]
        observed = [r for r in rows if r["execution_status"] != "not_executed"]
        entry.update(execution_coverage=ratio(len(observed), len(rows)),
                     observed_task_correctness=ratio(sum(r["grade"]["passed"] for r in observed), len(observed)),
                     execution_failure_rate=ratio(sum(r["execution_status"] == "failed" for r in observed), len(observed)),
                     not_executed=len(rows)-len(observed), measurements=usage([c for r in rows for c in r["calls"]]))
        # No old price-estimate columns, including misleading known-$0 subtotal.
        for key in ("total_cost_usd", "known_cost_subtotal_usd", "unknown_cost_attempts"):
            entry.pop(key, None)
    return stats


def rate(value):
    return "unknown" if value["value"] is None else "{}/{} ({:.1%})".format(value["numerator"], value["denominator"], value["value"])


def regenerate(directory):
    directory = Path(directory)
    read = lambda p: json.loads(p.read_text())
    metadata, plan = read(directory / "metadata.json"), read(directory / "plan.json")
    actual = {}
    if (directory / "attempts.jsonl").exists():
        for line in (directory / "attempts.jsonl").read_text().splitlines():
            try:
                record = json.loads(line)
                actual[record["attempt_id"]] = record
            except (ValueError, KeyError):
                continue
    records = [actual.get(p["attempt_id"], dict(p, output=None, error="interrupted_or_not_executed", calls=[],
               execution_status="not_executed", wall_ms=None, cost_usd=None, runnable=False, grade=p["failure_grade"])) for p in plan]
    stats = aggregate(records)
    builds = [read(p) for p in sorted((directory / "builds").glob("*/build.json"))]
    for arm in sorted({p["arm"] for p in plan if p["arm"].startswith("build_")} - {b["arm"] for b in builds}):
        builds.append({"arm": arm, "status": "not_executed", "syntax_valid": None, "calls": [], "wall_ms": None,
                       "boundary_correct": None, "boundary_total": metadata.get("workflow_probe_count"),
                       "human_rework_count": None, "human_rework_minutes": None, "candidate_sha256": None})
    for b in builds:
        selected = [r for r in records if r["arm"] == b["arm"]]
        b.update(candidate_cases_planned=len(selected), candidate_cases_runnable=sum(r["runnable"] for r in selected),
                 candidate_cases_correct=sum(r["grade"]["passed"] for r in selected), measurements=usage(b["calls"]))
    all_calls = [c for b in builds for c in b["calls"]] + [c for r in records for c in r["calls"]]
    # Calls belong to exactly one build or attempt; failed calls are retained.
    payload = {"metadata": metadata, "aggregate": stats, "builds": builds, "records": records,
               "all_measurements": usage(all_calls)}
    (directory / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    lines = ["# Codex supplier screening v2", "",
             "SIMULATION ONLY: software regression; no model evidence." if metadata["mode"] == "simulation" else
             "CODEX MEASURED: ChatGPT authentication; GPT-5.6 Sol / high. Account billing cost unknown.",
             "", "Run: `{}`; split: `{}`; stop: `{}`.".format(metadata["run_id"], metadata["split"], metadata.get("stop_reason")),
             "", "One paired repetition is descriptive; no Jev/DeepSeek/cheap-model or population claim.", "",
             "| Arm | Executed/planned | Correct/planned | Wrong release | Review | Actual completion | Median ms | Codex calls | Tools | Input/cache/output tokens |",
             "|---|---|---|---|---|---|---:|---:|---:|---|"]
    for arm, s in stats.items():
        m = s["measurements"]
        tokens = "/".join(str(m[k]) if m[k] is not None else "unknown" for k in ("input_tokens", "cached_input_tokens", "output_tokens"))
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            arm, rate(s["execution_coverage"]), rate(s["task_correctness"]), rate(s["wrong_automatic_release"]), rate(s["review_rate"]),
            rate(s["actual_completion_rate"]), s["median_wall_ms"], m["codex_calls"], m["tool_calls"], tokens))
    lines += ["", "Cached input is included in input tokens. Startup/context/return time included; grading excluded.",
              "Additional metrics with numerators, denominators and token completeness are in report.json.",
              "Prepared runner/task Skill preparation and required human rework are unknown. Billing is unknown, not zero.",
              "", "## Construction investment (separate from execution)", "",
              "| Arm | Status | Syntax | Runnable | Correct | Boundary decisions | Build ms | Calls | Input/cache/output tokens |",
              "|---|---|---|---|---|---|---:|---:|---|"]
    for b in builds:
        m = b["measurements"]
        lines.append("| {} | {} | {} | {}/{} | {}/{} | {}/{} | {} | {} | {} |".format(b["arm"], b["status"], b["syntax_valid"],
            b["candidate_cases_runnable"], b["candidate_cases_planned"], b["candidate_cases_correct"], b["candidate_cases_planned"],
            b["boundary_correct"], b["boundary_total"], b["wall_ms"], m["codex_calls"],
            "/".join(str(m[k]) if m[k] is not None else "unknown" for k in ("input_tokens", "cached_input_tokens", "output_tokens"))))
    if not builds:
        lines.append("\nConstruction was not executed.")
    lines += ["", "## Every scheduled attempt", "", "| Arm | Case | Execution | Status | Accepted | Failure reasons |", "|---|---|---|---|---|---|"]
    for r in records:
        state = r["output"].get("status", "invalid") if isinstance(r.get("output"), dict) else "unknown"
        reasons = "; ".join(r["grade"]["reasons"] + ([r["error"]] if r.get("error") else []))
        lines.append("| {} | {} | {} | {} | {} | {} |".format(r["arm"], r["case_id"], r["execution_status"], state, r["grade"]["passed"], reasons.replace("|", "\\|")))
    (directory / "report.md").write_text("\n".join(lines) + "\n")
    _, _, svg = quality_render(records, dict(metadata, mode=metadata["mode"]))
    svg = svg.replace("Observed task correctness", "Scheduled task acceptance")
    (directory / "comparison.svg").write_text(svg)
    return payload
