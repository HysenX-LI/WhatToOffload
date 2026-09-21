"""Bounded supplier evidence screening runner."""

import json
import sys
from decimal import Decimal, InvalidOperation


_MISSING = object()
_SEMANTIC_RESULTS = {
    "corroborated": ("completed", "eligible", "policy_satisfied"),
    "unrelated": ("completed", "ineligible", "reference_unrelated"),
    "conflict": ("needs_review", "undetermined", "reference_conflict"),
    "unclear": ("needs_review", "undetermined", "reference_unclear"),
}


def _money(value):
    """Return a finite, nonnegative, cent-exact Decimal or None."""
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


def _valid_text(document):
    value = document.get("text", _MISSING)
    return isinstance(value, str) and bool(value.strip())


def _normal_evidence(profile, regions, quote, reference):
    selected = (profile, regions, quote, reference)
    return [document["id"] for document in selected if document is not None]


def _reconcile_documents(vendor, requires_reference):
    """Reconcile source identity and choose authoritative source documents."""
    raw_documents = vendor.get("documents", _MISSING)
    if not isinstance(raw_documents, list):
        return {
            "terminal": _row(
                vendor.get("id"), "needs_input", "undetermined",
                ["missing_documents"], [],
            )
        }

    reasons = []
    by_id = {}
    unique_documents = []
    all_non_noise_ids = []

    for document in raw_documents:
        if not isinstance(document, dict) or not isinstance(document.get("id"), str):
            reasons.append("invalid_document")
            continue

        source_id = document["id"]
        if document.get("kind") != "noise":
            all_non_noise_ids.append(source_id)

        if source_id not in by_id:
            by_id[source_id] = document
            unique_documents.append(document)
        elif document != by_id[source_id]:
            reasons.append("conflicting_identity")
        # An exactly identical repeat is deliberately collapsed.

    documents = [d for d in unique_documents if d.get("kind") != "noise"]
    profiles = [d for d in documents if d.get("kind") == "profile"]
    references = [d for d in documents if d.get("kind") == "reference"]
    region_documents = [d for d in documents if d.get("kind") == "regions"]
    quotes = [d for d in documents if d.get("kind") == "quote"]

    if len(profiles) > 1 or len(region_documents) > 1:
        reasons.append("conflicting_documents")
    if requires_reference and len(references) > 1:
        reasons.append("conflicting_documents")

    profile = profiles[0] if len(profiles) == 1 else None
    regions = region_documents[0] if len(region_documents) == 1 else None
    reference = references[0] if requires_reference and len(references) == 1 else None

    valid_quotes = []
    invalid_revision = False
    for quote in quotes:
        revision = quote.get("revision")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision <= 0:
            invalid_revision = True
        else:
            valid_quotes.append(quote)
    if invalid_revision:
        reasons.append("invalid_revision")

    quote = None
    if valid_quotes:
        newest_revision = max(d["revision"] for d in valid_quotes)
        newest = [d for d in valid_quotes if d["revision"] == newest_revision]
        if len(newest) > 1:
            reasons.append("conflicting_revision")
        else:
            quote = newest[0]

    if not profiles:
        reasons.append("missing_profile")
    elif profile is not None and not _valid_text(profile):
        reasons.append("missing_profile_text")

    if not region_documents:
        reasons.append("missing_regions")
    elif regions is not None:
        values = regions.get("values", _MISSING)
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            reasons.append("missing_region_values")

    if not quotes:
        reasons.append("missing_quote")
    elif quote is not None:
        currency = quote.get("currency", _MISSING)
        if not isinstance(currency, str) or not currency:
            reasons.append("missing_currency")
        if _money(quote.get("amount", _MISSING)) is None:
            reasons.append("missing_or_invalid_amount")

    if requires_reference:
        if not references:
            reasons.append("missing_reference")
        elif reference is not None and not _valid_text(reference):
            reasons.append("missing_reference_text")

    conflict_codes = {
        "conflicting_identity", "conflicting_documents", "conflicting_revision"
    }
    missing_codes = {
        "invalid_document", "invalid_revision", "missing_profile",
        "missing_profile_text", "missing_regions", "missing_region_values",
        "missing_quote", "missing_currency", "missing_or_invalid_amount",
        "missing_reference", "missing_reference_text",
    }
    has_conflict = any(reason in conflict_codes for reason in reasons)
    has_missing = any(reason in missing_codes for reason in reasons)

    if has_conflict or invalid_revision:
        evidence_ids = all_non_noise_ids
    else:
        evidence_ids = _normal_evidence(profile, regions, quote, reference)

    if has_missing:
        status = "needs_input"
    elif has_conflict:
        status = "needs_review"
    else:
        status = None

    return {
        "status": status,
        "reasons": reasons,
        "evidence_ids": evidence_ids,
        "profile": profile,
        "regions": regions,
        "quote": quote,
        "reference": reference,
    }


def _semantic_outcome(answer, profile_id, reference_id):
    if not isinstance(answer, dict) or set(answer) != {"verdict", "evidence_ids"}:
        raise ValueError("invalid semantic response")
    verdict = answer["verdict"]
    evidence_ids = answer["evidence_ids"]
    expected_ids = [profile_id, reference_id]
    if (
        verdict not in _SEMANTIC_RESULTS
        or not isinstance(evidence_ids, list)
        or len(evidence_ids) != 2
        or any(not isinstance(value, str) for value in evidence_ids)
        or len(set(evidence_ids)) != 2
        or set(evidence_ids) != set(expected_ids)
    ):
        raise ValueError("invalid semantic response")
    return _SEMANTIC_RESULTS[verdict]


def _screen_vendor(vendor, policy, judge, max_price):
    vendor_id = vendor.get("id")
    reconciled = _reconcile_documents(vendor, policy["requires_reference"])
    if "terminal" in reconciled:
        return reconciled["terminal"], None

    if reconciled["status"] is not None:
        return _row(
            vendor_id,
            reconciled["status"],
            "undetermined",
            reconciled["reasons"],
            reconciled["evidence_ids"],
        ), None

    profile = reconciled["profile"]
    regions = reconciled["regions"]
    quote = reconciled["quote"]
    reference = reconciled["reference"]
    evidence_ids = reconciled["evidence_ids"]
    amount = _money(quote["amount"])

    hard_failures = []
    if quote["currency"] != policy["currency"]:
        hard_failures.append("currency_mismatch")
    if amount > max_price:
        hard_failures.append("over_budget")
    if not set(policy["required_regions"]).issubset(set(regions["values"])):
        hard_failures.append("region_mismatch")

    if hard_failures:
        return _row(
            vendor_id, "completed", "ineligible", hard_failures, evidence_ids
        ), None

    if not policy["requires_reference"]:
        return _row(
            vendor_id, "completed", "eligible", ["policy_satisfied"], evidence_ids
        ), amount

    try:
        answer = judge(policy["domain"], profile, reference)
        status, decision, reason = _semantic_outcome(
            answer, profile["id"], reference["id"]
        )
    except Exception:
        return _row(
            vendor_id,
            "failed",
            "undetermined",
            ["semantic_provider_failure"],
            evidence_ids,
        ), None

    row = _row(vendor_id, status, decision, [reason], evidence_ids)
    return row, amount if decision == "eligible" else None


def screen(payload, judge):
    """Screen every vendor in *payload* using an injected semantic judge."""
    policy = payload["policy"]
    vendors = payload["vendors"]
    max_price = _money(policy["max_price"])
    if max_price is None:
        raise ValueError("policy max_price must be nonnegative and cent-exact")

    rows = []
    eligible = []
    for vendor in vendors:
        row, amount = _screen_vendor(vendor, policy, judge, max_price)
        rows.append(row)
        if row["decision"] == "eligible":
            eligible.append((amount, row["id"]))

    shortlist = [vendor_id for _, vendor_id in sorted(eligible, key=lambda item: (item[0], item[1]))]

    row_statuses = {row["status"] for row in rows}
    if "failed" in row_statuses:
        status = "failed"
    elif not vendors or "needs_input" in row_statuses:
        status = "needs_input"
    elif "needs_review" in row_statuses:
        status = "needs_review"
    elif policy["action"] == "prepare_contact" and shortlist:
        status = "needs_approval"
    else:
        status = "completed"

    approval_required = status == "needs_approval"
    return {
        "request_id": payload["request_id"],
        "status": status,
        "summary": "Screened {} vendor record(s); no external action performed.".format(len(vendors)),
        "rows": rows,
        "shortlist": shortlist,
        "approval_required": approval_required,
        "action_performed": False,
    }


def main():
    from semantic_bridge import judge

    payload = json.loads(sys.stdin.readline())
    result = screen(payload, judge)
    sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
