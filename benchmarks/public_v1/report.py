"""Regenerate reports solely from preserved attempt records (no model calls)."""
import html
import json
import statistics
from pathlib import Path


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def aggregate(records):
    groups = {}
    for record in records:
        groups.setdefault(record["arm"], []).append(record)
    result = {}
    for arm, rows in sorted(groups.items()):
        def total(key):
            return sum(r["grade"].get(key, 0) for r in rows)
        times = [r["wall_ms"] for r in rows if r.get("wall_ms") is not None]
        costs = [r.get("cost_usd") for r in rows]
        n = len(rows)
        result[arm] = {
            "attempts": n, "task_correctness": ratio(total("passed"), n),
            "wrong_automatic_release": ratio(total("wrong_releases"), total("predicted_eligible")),
            "review_rate": ratio(total("review_rows"), total("expected_rows")),
            "correct_review_recall": ratio(total("correct_review_rows"), total("gold_review_rows")),
            "citation_precision": ratio(total("correct_citations"), total("citations")),
            "omission_rate": ratio(total("omitted_rows"), total("expected_rows")),
            "record_accuracy": ratio(total("correct_rows"), total("expected_rows")),
            "actual_completion_rate": ratio(total("actual_completion"), n),
            "execution_failure_rate": ratio(sum(r["execution_status"] != "completed" for r in rows), n),
            "correct_input_handoffs": total("correct_input_handoff"),
            "correct_approval_handoffs": total("correct_approval_handoff"),
            "median_wall_ms": statistics.median(times) if times else None,
            "timed_attempts": len(times),
            "total_cost_usd": sum(costs) if all(c is not None for c in costs) else None,
            "known_cost_subtotal_usd": sum(c for c in costs if c is not None),
            "unknown_cost_attempts": sum(c is None for c in costs),
        }
    return result


def render(records, metadata):
    stats = aggregate(records)
    mode = metadata["mode"]
    warning = ("OFFLINE SIMULATION: validates software only. Agent arms, model quality, production latency and model costs are unmeasured."
               if mode == "offline" else "LIVE OBSERVATIONS: see frozen protocol, setup exclusions and per-attempt errors. No generalization guarantee.")
    def rate(value):
        return "unknown" if value["value"] is None else "{}/{} ({:.1%})".format(value["numerator"], value["denominator"], value["value"])
    lines = ["# Public supplier screening", "", warning, "", "Run: `" + metadata["run_id"] + "` · split: `" + metadata["split"] + "`", "",
             "| Arm | Attempts | Correct | Wrong release | Review | Actual completion | Failure | Median ms | USD upper estimate |",
             "|---|---:|---|---|---|---|---|---:|---:|"]
    for arm, s in stats.items():
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            arm, s["attempts"], rate(s["task_correctness"]), rate(s["wrong_automatic_release"]), rate(s["review_rate"]),
            rate(s["actual_completion_rate"]), rate(s["execution_failure_rate"]), s["median_wall_ms"],
            "unknown" if s["total_cost_usd"] is None else "{:.6f}".format(s["total_cost_usd"])))
    lines += ["", "All numerators/denominators, citation precision, omissions and handoff counts are in report.json.",
              "Preparation/human rework costs are unknown unless explicitly recorded in build records.", "", "## Every attempt", "",
              "| Arm | Case | Repeat | Execution | Workflow status | Grade | Reasons |", "|---|---|---:|---|---|---|---|"]
    for r in records:
        reasons = "; ".join(r["grade"]["reasons"]) or "—"
        if r.get("error"):
            reasons += "; " + r["error"]
        state = r["output"].get("status", "invalid") if isinstance(r.get("output"), dict) else "unavailable"
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(r["arm"], r["case_id"], r["repetition"], r["execution_status"], state, "pass" if r["grade"]["passed"] else "FAIL", reasons.replace("|", "\\|")))
    height = 110 + 65 * len(stats)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="980" height="{}" viewBox="0 0 980 {}">'.format(height, height),
           '<rect width="100%" height="100%" fill="white"/>',
           '<g font-family="sans-serif" fill="#111827"><text x="24" y="30" font-size="20">Observed task correctness — {}</text>'.format(html.escape(mode)),
           '<text x="24" y="55" font-size="12">{} attempts; correctness includes required handoffs. Completion is reported separately.</text>'.format(len(records))]
    for i, (arm, s) in enumerate(stats.items()):
        y = 95 + i * 65
        value = s["task_correctness"]["value"] or 0
        svg += ['<text x="24" y="{}" font-size="13">{}</text>'.format(y, html.escape(arm)),
                '<rect x="285" y="{}" width="{}" height="20" fill="#2563eb"/>'.format(y-16, 350*value),
                '<text x="650" y="{}" font-size="13">{}</text>'.format(y, html.escape(rate(s["task_correctness"])))]
    svg.append('</g></svg>')
    return {"metadata": metadata, "aggregate": stats, "records": records}, "\n".join(lines) + "\n", "\n".join(svg) + "\n"


def write_report(directory, records, metadata):
    data, markdown, svg = render(records, metadata)
    directory = Path(directory)
    (directory / "report.json").write_text(json.dumps(data, indent=2) + "\n")
    (directory / "report.md").write_text(markdown)
    (directory / "comparison.svg").write_text(svg)
