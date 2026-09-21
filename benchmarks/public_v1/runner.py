"""Code-owned policy. This module never reads fixtures, gold or evaluator files."""
import argparse
import json
import sys

from benchmarks.contracts import string_list
from .contracts import result_errors, validate_judgment
from .helpers import money


def row_result(vendor_id, status, reason, evidence, decision="undetermined"):
    return {"id": vendor_id, "status": status, "decision": decision,
            "reasons": sorted(reason), "evidence_ids": sorted(set(evidence))}


def documents_for(vendor, policy):
    """Normalize identical deliveries; conflicting identities cannot be trusted."""
    documents = vendor.get("documents")
    if not isinstance(documents, list):
        return {}, [], ["missing_documents"]
    by_id = {}
    conflict = False
    for doc in documents:
        if (not isinstance(doc, dict) or not isinstance(doc.get("id"), str) or not doc["id"].strip()
                or not isinstance(doc.get("kind"), str) or doc["kind"] not in {"profile", "reference", "regions", "quote", "noise"}):
            return {}, [], ["invalid_document"]
        if doc.get("kind") == "noise":
            continue
        if doc["id"] in by_id and by_id[doc["id"]] != doc:
            conflict = True
        by_id[doc["id"]] = doc
    if conflict:
        return {}, sorted(by_id), ["conflicting_identity"]
    grouped = {}
    for doc in by_id.values():
        grouped.setdefault(doc.get("kind"), []).append(doc)
    selected = {}
    for kind in ("profile", "regions", "reference"):
        if kind == "reference" and not policy["requires_reference"]:
            continue
        group = grouped.get(kind, [])
        if len(group) > 1:
            return {}, sorted(by_id), ["conflicting_documents"]
        if group:
            selected[kind] = group[0]
    quotes = grouped.get("quote", [])
    if any(type(q.get("revision")) is not int or q["revision"] < 1 for q in quotes):
        return {}, sorted(by_id), ["invalid_revision"]
    if quotes:
        revision = max(q["revision"] for q in quotes)
        newest = [q for q in quotes if q["revision"] == revision]
        if len(newest) != 1:
            return {}, sorted(by_id), ["conflicting_revision"]
        selected["quote"] = newest[0]
    return selected, sorted(d["id"] for d in selected.values()), []


def screen_vendor(vendor, policy, judge):
    vendor_id = vendor["id"]
    selected, evidence, problems = documents_for(vendor, policy)
    if problems:
        review = any(x.startswith("conflicting") for x in problems)
        return row_result(vendor_id, "needs_review" if review else "needs_input", problems, evidence), None
    required = ["profile", "regions", "quote"] + (["reference"] if policy["requires_reference"] else [])
    missing = ["missing_" + kind for kind in required if kind not in selected]
    for kind in ("profile", "reference"):
        if kind in selected and (not isinstance(selected[kind].get("text"), str) or not selected[kind]["text"].strip()):
            missing.append("missing_" + kind + "_text")
    if "regions" in selected and not string_list(selected["regions"].get("values")):
        missing.append("missing_region_values")
    price = None
    if "quote" in selected:
        quote = selected["quote"]
        if not isinstance(quote.get("currency"), str) or not quote["currency"].strip():
            missing.append("missing_currency")
        try:
            price = money(quote.get("amount"))
        except (ValueError, ArithmeticError):
            missing.append("missing_or_invalid_amount")
    if missing:
        return row_result(vendor_id, "needs_input", missing, evidence), price
    reasons = []
    if selected["quote"]["currency"] != policy["currency"]:
        reasons.append("currency_mismatch")
    if price > money(policy["max_price"]):
        reasons.append("over_budget")
    if not set(policy["required_regions"]).issubset(selected["regions"]["values"]):
        reasons.append("region_mismatch")
    if reasons:
        return row_result(vendor_id, "completed", reasons, evidence, "ineligible"), price
    if policy["requires_reference"]:
        try:
            response = judge(policy["domain"], selected["profile"], selected["reference"])
            verdict = validate_judgment(response, selected["profile"], selected["reference"])
        except Exception:
            return row_result(vendor_id, "failed", ["semantic_provider_failure"], evidence), price
        if verdict in {"conflict", "unclear"}:
            return row_result(vendor_id, "needs_review", ["reference_" + verdict], evidence), price
        if verdict == "unrelated":
            return row_result(vendor_id, "completed", ["reference_unrelated"], evidence, "ineligible"), price
    return row_result(vendor_id, "completed", ["policy_satisfied"], evidence, "eligible"), price


def input_valid(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("request_id"), str) or not payload["request_id"]:
        return False
    policy = payload.get("policy")
    if not isinstance(policy, dict):
        return False
    if any(not isinstance(policy.get(k), str) or not policy[k] for k in ("domain", "currency")):
        return False
    if not string_list(policy.get("required_regions")) or type(policy.get("requires_reference")) is not bool:
        return False
    if policy.get("action") not in ("screen", "prepare_contact"):
        return False
    try:
        money(policy.get("max_price"))
    except (ValueError, ArithmeticError):
        return False
    vendors = payload.get("vendors")
    if not isinstance(vendors, list):
        return False
    ids = [v.get("id") if isinstance(v, dict) else None for v in vendors]
    return all(isinstance(v, str) and v for v in ids) and len(ids) == len(set(ids))


def screen(payload, judge):
    """Pure bounded runner; judge(domain, profile, reference) is the only dependency."""
    request_id = payload.get("request_id", "invalid") if isinstance(payload, dict) else "invalid"
    if not isinstance(request_id, str) or not request_id.strip():
        request_id = "invalid"
    if not input_valid(payload):
        return {"request_id": request_id or "invalid", "status": "needs_input", "summary": "Invalid request; provide required typed fields.",
                "rows": [], "shortlist": [], "approval_required": False, "action_performed": False}
    rows, ranking = [], []
    for vendor in payload["vendors"]:
        row, price = screen_vendor(vendor, payload["policy"], judge)
        rows.append(row)
        if row["decision"] == "eligible":
            ranking.append((price, vendor["id"]))
    shortlist = [vendor_id for _, vendor_id in sorted(ranking)]
    statuses = {r["status"] for r in rows}
    status = next((s for s in ("failed", "needs_input", "needs_review") if s in statuses), "completed")
    if not rows:
        status = "needs_input"
    if status == "completed" and shortlist and payload["policy"]["action"] == "prepare_contact":
        status = "needs_approval"
    result = {"request_id": request_id, "status": status,
              "summary": "Screened {} vendor record(s); no external action performed.".format(len(rows)),
              "rows": rows, "shortlist": shortlist, "approval_required": status == "needs_approval", "action_performed": False}
    if result_errors(payload, result):
        raise RuntimeError("runner output contract failed")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="JSON input file; defaults to stdin")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--config")
    args = parser.parse_args()
    from .providers import OfflineJudge, live_client, SemanticJudge
    if args.live:
        if not args.config:
            parser.error("--live requires an authorized --config")
        judge = SemanticJudge(live_client(args.config))
    else:
        judge = OfflineJudge()
    try:
        if args.input:
            with open(args.input, encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = None
    print(json.dumps(screen(payload, judge), ensure_ascii=False))


if __name__ == "__main__":
    main()
