"""Bounded supplier evidence screening runner.

The semantic judge is deliberately passed in by the caller. All business fields,
policy checks, result construction, and action controls remain local to this file.
"""

import json
import sys
from decimal import Decimal, DecimalException


def _money(value):
    """Return a finite, nonnegative, cent-exact Decimal or None."""
    if not isinstance(value, str):
        return None
    try:
        number = Decimal(value)
        if (
            not number.is_finite()
            or number < 0
            or number != number.quantize(Decimal("0.01"))
        ):
            return None
        return number
    except (DecimalException, ValueError):
        return None


def _fingerprint(document):
    """Type-sensitive, object-key-order-insensitive identity for JSON documents."""
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def _row(vendor, policy, judge):
    vendor_id = vendor.get("id")
    documents_present = "documents" in vendor and isinstance(
        vendor.get("documents"), list
    )
    raw_documents = vendor.get("documents") if documents_present else []

    invalid_document = False
    by_id = {}
    identity_conflict = False
    all_non_noise_ids = set()

    for document in raw_documents:
        if not isinstance(document, dict):
            invalid_document = True
            continue
        source_id = document.get("id")
        if not isinstance(source_id, str):
            invalid_document = True
            continue
        if document.get("kind") != "noise":
            all_non_noise_ids.add(source_id)
        fingerprint = _fingerprint(document)
        if source_id in by_id:
            if by_id[source_id][0] != fingerprint:
                identity_conflict = True
            continue
        by_id[source_id] = (fingerprint, document)

    documents = [entry[1] for entry in by_id.values()]
    if identity_conflict:
        return {
            "id": vendor_id,
            "status": "needs_review",
            "decision": "undetermined",
            "reasons": ["conflicting_identity"],
            "evidence_ids": sorted(all_non_noise_ids),
        }, None

    profiles = [item for item in documents if item.get("kind") == "profile"]
    references = [item for item in documents if item.get("kind") == "reference"]
    regions = [item for item in documents if item.get("kind") == "regions"]
    quotes = [item for item in documents if item.get("kind") == "quote"]
    reference_required = policy.get("requires_reference") is True

    if (
        len(profiles) > 1
        or len(regions) > 1
        or (reference_required and len(references) > 1)
    ):
        return {
            "id": vendor_id,
            "status": "needs_review",
            "decision": "undetermined",
            "reasons": ["conflicting_documents"],
            "evidence_ids": sorted(all_non_noise_ids),
        }, None

    invalid_revision = any(
        not isinstance(item.get("revision"), int)
        or isinstance(item.get("revision"), bool)
        or item.get("revision") <= 0
        for item in quotes
    )
    if invalid_revision:
        return {
            "id": vendor_id,
            "status": "needs_input",
            "decision": "undetermined",
            "reasons": ["invalid_revision"],
            "evidence_ids": sorted(all_non_noise_ids),
        }, None

    selected_quote = None
    if quotes:
        newest_revision = max(item["revision"] for item in quotes)
        newest_quotes = [
            item for item in quotes if item["revision"] == newest_revision
        ]
        if len(newest_quotes) > 1:
            return {
                "id": vendor_id,
                "status": "needs_review",
                "decision": "undetermined",
                "reasons": ["conflicting_revision"],
                "evidence_ids": sorted(all_non_noise_ids),
            }, None
        selected_quote = newest_quotes[0]

    profile = profiles[0] if profiles else None
    reference = references[0] if reference_required and references else None
    region_document = regions[0] if regions else None

    selected_documents = [profile, region_document, selected_quote]
    if reference_required:
        selected_documents.append(reference)
    evidence_ids = sorted(
        item["id"] for item in selected_documents if item is not None
    )

    reasons = []
    if not documents_present:
        reasons.append("missing_documents")
    if invalid_document:
        reasons.append("invalid_document")
    if profile is None:
        reasons.append("missing_profile")
    elif not isinstance(profile.get("text"), str) or not profile.get("text"):
        reasons.append("missing_profile_text")
    if region_document is None:
        reasons.append("missing_regions")
    else:
        values = region_document.get("values")
        if not isinstance(values, list) or any(
            not isinstance(value, str) for value in values
        ):
            reasons.append("missing_region_values")
    if selected_quote is None:
        reasons.append("missing_quote")
        amount = None
    else:
        if not isinstance(selected_quote.get("currency"), str) or not selected_quote.get(
            "currency"
        ):
            reasons.append("missing_currency")
        amount = _money(selected_quote.get("amount"))
        if amount is None:
            reasons.append("missing_or_invalid_amount")
    if reference_required:
        if reference is None:
            reasons.append("missing_reference")
        elif not isinstance(reference.get("text"), str) or not reference.get("text"):
            reasons.append("missing_reference_text")

    if reasons:
        return {
            "id": vendor_id,
            "status": "needs_input",
            "decision": "undetermined",
            "reasons": sorted(set(reasons)),
            "evidence_ids": evidence_ids,
        }, None

    failures = []
    if selected_quote["currency"] != policy.get("currency"):
        failures.append("currency_mismatch")
    maximum = _money(policy.get("max_price"))
    if maximum is None:
        # The policy contract says this cannot occur. Treat it as unusable input
        # rather than allowing an invalid policy to bypass its price ceiling.
        return {
            "id": vendor_id,
            "status": "needs_input",
            "decision": "undetermined",
            "reasons": ["missing_or_invalid_amount"],
            "evidence_ids": evidence_ids,
        }, None
    if amount > maximum:
        failures.append("over_budget")
    required_regions = policy.get("required_regions", [])
    if any(region not in region_document["values"] for region in required_regions):
        failures.append("region_mismatch")
    if failures:
        return {
            "id": vendor_id,
            "status": "completed",
            "decision": "ineligible",
            "reasons": sorted(failures),
            "evidence_ids": evidence_ids,
        }, None

    if reference_required:
        try:
            # Send only the two fields needed for semantic comparison and
            # attribution. The judge never receives price, region, or action data.
            result = judge(
                policy.get("domain"),
                {"id": profile["id"], "text": profile["text"]},
                {"id": reference["id"], "text": reference["text"]},
            )
            if not isinstance(result, dict) or set(result) != {
                "verdict",
                "evidence_ids",
            }:
                raise ValueError("invalid semantic response shape")
            semantic_ids = result["evidence_ids"]
            expected_ids = {profile["id"], reference["id"]}
            if (
                not isinstance(semantic_ids, list)
                or len(semantic_ids) != 2
                or any(not isinstance(item, str) for item in semantic_ids)
                or set(semantic_ids) != expected_ids
            ):
                raise ValueError("invalid semantic evidence")
            verdicts = {
                "corroborated": ("completed", "eligible", "policy_satisfied"),
                "unrelated": ("completed", "ineligible", "reference_unrelated"),
                "conflict": ("needs_review", "undetermined", "reference_conflict"),
                "dispute": ("needs_review", "undetermined", "reference_conflict"),
                "unclear": ("needs_review", "undetermined", "reference_unclear"),
            }
            if result["verdict"] not in verdicts:
                raise ValueError("invalid semantic verdict")
            status, decision, reason = verdicts[result["verdict"]]
        except Exception:
            return {
                "id": vendor_id,
                "status": "failed",
                "decision": "undetermined",
                "reasons": ["semantic_provider_failure"],
                "evidence_ids": evidence_ids,
            }, None
        return {
            "id": vendor_id,
            "status": status,
            "decision": decision,
            "reasons": [reason],
            "evidence_ids": evidence_ids,
        }, amount if decision == "eligible" else None

    return {
        "id": vendor_id,
        "status": "completed",
        "decision": "eligible",
        "reasons": ["policy_satisfied"],
        "evidence_ids": evidence_ids,
    }, amount


def screen(payload, judge):
    """Screen every supplied vendor and return the bounded factual receipt."""
    policy = payload.get("policy", {})
    vendors = payload.get("vendors", [])
    if not isinstance(vendors, list):
        vendors = []

    rows = []
    eligible = []
    for vendor in vendors:
        # Vendor objects and unique string IDs are guaranteed by the input contract.
        row, price = _row(vendor, policy, judge)
        rows.append(row)
        if price is not None:
            eligible.append((price, row["id"]))

    shortlist = [vendor_id for _, vendor_id in sorted(eligible)]
    if not vendors:
        status = "needs_input"
    elif any(row["status"] == "failed" for row in rows):
        status = "failed"
    elif any(row["status"] == "needs_input" for row in rows):
        status = "needs_input"
    elif any(row["status"] == "needs_review" for row in rows):
        status = "needs_review"
    elif policy.get("action") == "prepare_contact" and shortlist:
        status = "needs_approval"
    else:
        status = "completed"

    return {
        "request_id": payload.get("request_id"),
        "status": status,
        "summary": "Screened {} vendor record(s); no external action performed.".format(
            len(vendors)
        ),
        "rows": rows,
        "shortlist": shortlist,
        "approval_required": status == "needs_approval",
        "action_performed": False,
    }


def _main():
    from semantic_bridge import judge

    payload = json.loads(sys.stdin.readline())
    result = screen(payload, judge)
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    _main()
