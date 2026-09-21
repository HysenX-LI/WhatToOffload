"""Bounded supplier-evidence screening runner."""

from __future__ import annotations

import json
import sys
from decimal import Decimal, InvalidOperation


def _money(value):
    """Return a non-negative, finite, cent-exact Decimal, or None."""
    if not isinstance(value, str):
        return None
    try:
        result = Decimal(value)
        cents = result.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    if not result.is_finite() or result < 0 or result != cents:
        return None
    return result


def _row(vendor_id, status, decision, reasons, evidence_ids):
    return {
        "id": vendor_id,
        "status": status,
        "decision": decision,
        "reasons": sorted(set(reasons)),
        "evidence_ids": sorted(set(evidence_ids)),
    }


def _all_source_ids(documents):
    """IDs used by the special conflict/invalid-revision citation rule."""
    return [
        document["id"]
        for document in documents
        if isinstance(document, dict)
        and document.get("kind") != "noise"
        and isinstance(document.get("id"), str)
    ]


def _screen_vendor(vendor, policy, judge):
    vendor_id = vendor.get("id") if isinstance(vendor, dict) else None
    if not isinstance(vendor, dict) or "documents" not in vendor or not isinstance(
        vendor.get("documents"), list
    ):
        return _row(
            vendor_id, "needs_input", "undetermined", ["missing_documents"], []
        ), None

    original_documents = vendor["documents"]
    all_ids = _all_source_ids(original_documents)

    # Noise is wholly outside the evidence set. Other malformed documents are
    # retained as missing-input facts but cannot supply an evidence ID.
    invalid_document = False
    documents = []
    for document in original_documents:
        if isinstance(document, dict) and document.get("kind") == "noise":
            continue
        if not isinstance(document, dict) or not isinstance(document.get("id"), str):
            invalid_document = True
            continue
        documents.append(document)

    # Collapse only byte-for-byte-equivalent (as JSON values) repeated sources.
    by_id = {}
    fingerprints = {}
    conflicting_identity = False
    for document in documents:
        source_id = document["id"]
        # Canonical JSON preserves distinctions such as true versus 1 and 1
        # versus 1.0, while disregarding irrelevant object-key order.
        fingerprint = json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        if source_id not in by_id:
            by_id[source_id] = document
            fingerprints[source_id] = fingerprint
        elif fingerprints[source_id] != fingerprint:
            conflicting_identity = True
    documents = list(by_id.values())

    if conflicting_identity:
        return _row(
            vendor_id,
            "needs_review",
            "undetermined",
            ["conflicting_identity"],
            all_ids,
        ), None

    profiles = [d for d in documents if d.get("kind") == "profile"]
    regions_docs = [d for d in documents if d.get("kind") == "regions"]
    references = (
        [d for d in documents if d.get("kind") == "reference"]
        if policy.get("requires_reference") is True
        else []
    )
    quotes = [d for d in documents if d.get("kind") == "quote"]

    conflict_reasons = []
    if len(profiles) > 1 or len(regions_docs) > 1 or len(references) > 1:
        conflict_reasons.append("conflicting_documents")

    valid_quotes = []
    invalid_revision = False
    for quote in quotes:
        revision = quote.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision <= 0:
            invalid_revision = True
        else:
            valid_quotes.append(quote)

    if valid_quotes:
        highest_revision = max(q["revision"] for q in valid_quotes)
        newest_quotes = [q for q in valid_quotes if q["revision"] == highest_revision]
        if len(newest_quotes) > 1:
            conflict_reasons.append("conflicting_revision")

    if conflict_reasons:
        return _row(
            vendor_id,
            "needs_review",
            "undetermined",
            conflict_reasons,
            all_ids,
        ), None
    profile = profiles[0] if profiles else None
    regions_doc = regions_docs[0] if regions_docs else None
    reference = references[0] if references else None
    quote = newest_quotes[0] if valid_quotes else None

    selected = [d for d in (profile, regions_doc, quote, reference) if d is not None]
    evidence_ids = [d["id"] for d in selected]
    missing = []
    if invalid_document:
        missing.append("invalid_document")
    if invalid_revision:
        missing.append("invalid_revision")
    if profile is None:
        missing.append("missing_profile")
    elif not isinstance(profile.get("text"), str) or not profile.get("text"):
        missing.append("missing_profile_text")
    if regions_doc is None:
        missing.append("missing_regions")
    elif not isinstance(regions_doc.get("values"), list):
        missing.append("missing_region_values")
    if quote is None and not quotes:
        missing.append("missing_quote")
        amount = None
    elif quote is None:
        # One or more quote documents exist, but every revision is unusable.
        amount = None
    else:
        if not isinstance(quote.get("currency"), str) or not quote.get("currency"):
            missing.append("missing_currency")
        amount = _money(quote.get("amount"))
        if amount is None:
            missing.append("missing_or_invalid_amount")
    if policy.get("requires_reference") is True:
        if reference is None:
            missing.append("missing_reference")
        elif not isinstance(reference.get("text"), str) or not reference.get("text"):
            missing.append("missing_reference_text")

    if missing:
        return _row(
            vendor_id,
            "needs_input",
            "undetermined",
            missing,
            all_ids if invalid_revision else evidence_ids,
        ), None

    hard_failures = []
    if quote["currency"] != policy.get("currency"):
        hard_failures.append("currency_mismatch")
    budget = _money(policy.get("max_price"))
    # The policy schema guarantees a valid budget; treating an invalid policy as
    # a provider-independent failure avoids accidentally approving a quote.
    if budget is None or amount > budget:
        hard_failures.append("over_budget")
    required_regions = policy.get("required_regions", [])
    if not all(region in regions_doc["values"] for region in required_regions):
        hard_failures.append("region_mismatch")
    if hard_failures:
        return _row(
            vendor_id, "completed", "ineligible", hard_failures, evidence_ids
        ), None

    if policy.get("requires_reference") is not True:
        return _row(
            vendor_id,
            "completed",
            "eligible",
            ["policy_satisfied"],
            evidence_ids,
        ), amount

    try:
        # Supply only the source evidence fields, unchanged. In particular,
        # document extensions cannot become semantic instructions.
        profile_evidence = {
            "id": profile["id"],
            "text": profile["text"],
            "kind": profile["kind"],
        }
        reference_evidence = {
            "id": reference["id"],
            "text": reference["text"],
            "kind": reference["kind"],
        }
        answer = judge(policy.get("domain"), profile_evidence, reference_evidence)
        expected_ids = {profile["id"], reference["id"]}
        valid_answer = (
            isinstance(answer, dict)
            and set(answer) == {"verdict", "evidence_ids"}
            and isinstance(answer.get("verdict"), str)
            and isinstance(answer.get("evidence_ids"), list)
            and len(answer["evidence_ids"]) == 2
            and all(isinstance(item, str) for item in answer["evidence_ids"])
            and set(answer["evidence_ids"]) == expected_ids
        )
        if not valid_answer:
            raise ValueError("invalid semantic response")
        verdict = answer["verdict"]
        outcomes = {
            "corroborated": ("completed", "eligible", "policy_satisfied"),
            "unrelated": ("completed", "ineligible", "reference_unrelated"),
            "conflict": ("needs_review", "undetermined", "reference_conflict"),
            "unclear": ("needs_review", "undetermined", "reference_unclear"),
        }
        if verdict not in outcomes:
            raise ValueError("unknown semantic verdict")
        status, decision, reason = outcomes[verdict]
        eligible_amount = amount if decision == "eligible" else None
        return _row(vendor_id, status, decision, [reason], evidence_ids), eligible_amount
    except Exception:
        return _row(
            vendor_id,
            "failed",
            "undetermined",
            ["semantic_provider_failure"],
            evidence_ids,
        ), None


def screen(payload, judge):
    """Screen all vendor records in *payload* using the supplied semantic judge."""
    policy = payload.get("policy", {})
    vendors = payload.get("vendors", [])
    rows = []
    eligible = []
    for vendor in vendors:
        row, amount = _screen_vendor(vendor, policy, judge)
        rows.append(row)
        if row["decision"] == "eligible":
            eligible.append((amount, row["id"]))

    shortlist = [vendor_id for _, vendor_id in sorted(eligible, key=lambda x: (x[0], x[1]))]
    row_statuses = {row["status"] for row in rows}
    if "failed" in row_statuses:
        status = "failed"
    elif not vendors or "needs_input" in row_statuses:
        status = "needs_input"
    elif "needs_review" in row_statuses:
        status = "needs_review"
    elif policy.get("action") == "prepare_contact" and shortlist:
        status = "needs_approval"
    else:
        status = "completed"

    approval_required = status == "needs_approval"
    return {
        "request_id": payload.get("request_id"),
        "status": status,
        "summary": "Screened {} vendor record(s); no external action performed.".format(
            len(vendors)
        ),
        "rows": rows,
        "shortlist": shortlist,
        "approval_required": approval_required,
        "action_performed": False,
    }


def _main():
    from semantic_bridge import judge

    payload = json.loads(sys.stdin.readline())
    result = screen(payload, judge)
    print(json.dumps(result, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    _main()
