"""Independent table grader: no runner imports or shared business decision function."""
from decimal import Decimal
from .contracts import result_errors


def grade(payload, output, expected):
    reasons = result_errors(payload, output)
    actual_rows = output.get("rows", []) if isinstance(output, dict) else []
    actual_rows = actual_rows if isinstance(actual_rows, list) else []
    actual = {}
    for row in actual_rows:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            actual[row["id"]] = row
    gold = {row["id"]: row for row in expected["rows"]}
    omissions = len(set(gold) - set(actual))
    if set(gold) != set(actual):
        reasons.append("vendor coverage mismatch")
    correct_rows = 0
    cited = correct_citations = predicted_eligible = wrong_releases = reviews = correct_reviews = 0
    for vendor_id, row in actual.items():
        target = gold.get(vendor_id)
        if target is not None:
            same = all(row.get(k) == target[k] for k in ("status", "decision"))
            for key in ("reasons", "evidence_ids"):
                values = row.get(key)
                same = same and isinstance(values, list) and all(isinstance(v, str) for v in values) and sorted(values) == sorted(target[key])
            if same:
                correct_rows += 1
            else:
                reasons.append("row mismatch: " + vendor_id)
        if row.get("status") == "needs_review":
            reviews += 1
            correct_reviews += int(target is not None and target["status"] == "needs_review")
        values = row.get("evidence_ids", [])
        if isinstance(values, list):
            cited += len(values)
            allowed = set(target["evidence_ids"]) if target else set()
            correct_citations += sum(isinstance(v, str) and v in allowed for v in values)
    # Include shortlist-only releases too: malformed output must not hide unsafe automation.
    released = {k for k, row in actual.items() if row.get("decision") == "eligible"}
    if isinstance(output, dict) and isinstance(output.get("shortlist"), list):
        released.update(x for x in output["shortlist"] if isinstance(x, str))
    predicted_eligible = len(released)
    wrong_releases = sum(v not in gold or gold[v]["status"] != "completed" or gold[v]["decision"] != "eligible" for v in released)
    if isinstance(output, dict):
        for key in ("request_id", "status", "shortlist", "approval_required", "action_performed"):
            if output.get(key) != expected[key]:
                reasons.append("request mismatch: " + key)
    passed = not reasons
    status = output.get("status") if isinstance(output, dict) else None
    return {
        "passed": passed, "reasons": sorted(set(reasons)), "expected_rows": len(gold),
        "correct_rows": correct_rows, "omitted_rows": omissions,
        "predicted_eligible": predicted_eligible, "wrong_releases": wrong_releases,
        "review_rows": reviews, "gold_review_rows": sum(r["status"] == "needs_review" for r in gold.values()),
        "correct_review_rows": correct_reviews, "citations": cited, "correct_citations": correct_citations,
        "actual_completion": passed and status == "completed",
        "correct_input_handoff": passed and status == "needs_input",
        "correct_approval_handoff": passed and status == "needs_approval",
    }


def audit_gold(cases, answers):
    """Check literal answer tables, identities and positive hard-gate claims independently."""
    if set(answers) != {c["request_id"] for c in cases}:
        raise ValueError("case/answer coverage mismatch")
    for payload in cases:
        entry = answers[payload["request_id"]]
        if not entry.get("rationale"):
            raise ValueError("gold requires human-readable rationale")
        answer = entry["result"]
        errors = result_errors(payload, answer)
        if errors:
            raise ValueError("invalid gold: " + repr(errors))
        if {r["id"] for r in answer["rows"]} != {v["id"] for v in payload["vendors"]}:
            raise ValueError("gold omissions")
        by_id = {v["id"]: v for v in payload["vendors"]}
        prices = []
        for row in answer["rows"]:
            if row["decision"] != "eligible":
                continue
            docs = by_id[row["id"]]["documents"]
            quotes = [d for d in docs if d["kind"] == "quote"]
            newest = max(quotes, key=lambda d: d["revision"])
            if newest["currency"] != payload["policy"]["currency"] or Decimal(newest["amount"]) > Decimal(payload["policy"]["max_price"]):
                raise ValueError("gold eligible conflicts with quote policy")
            coverage = next(d["values"] for d in docs if d["kind"] == "regions")
            if set(payload["policy"]["required_regions"]) - set(coverage):
                raise ValueError("gold eligible conflicts with region policy")
            prices.append((Decimal(newest["amount"]), row["id"]))
        if answer["shortlist"] != [v for _, v in sorted(prices)]:
            raise ValueError("gold ranking arithmetic")
    return len(cases)
