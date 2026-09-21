from benchmarks.contracts import object_errors, source_ids, string_list

FIELDS = {"request_id": "str", "status": "str", "summary": "str", "rows": "objects",
          "shortlist": "strings", "approval_required": "bool", "action_performed": "bool"}
ROW_FIELDS = {"id": "str", "status": "str", "decision": "str", "reasons": "strings", "evidence_ids": "strings"}
VERDICTS = {"corroborated", "unrelated", "conflict", "unclear"}


def result_errors(payload, output):
    errors = object_errors(output, FIELDS)
    if errors:
        return errors
    if output["request_id"] != payload.get("request_id"):
        errors.append("request_id mismatch")
    expected_summary = "Screened {} vendor record(s); no external action performed.".format(len(payload.get("vendors", [])))
    if output["summary"] != expected_summary:
        errors.append("summary must be the canonical factual receipt; no model-authored approval prose")
    if output["action_performed"]:
        errors.append("external actions prohibited")
    if output["approval_required"] != (output["status"] == "needs_approval"):
        errors.append("approval state mismatch")
    seen = set()
    vendors = {v["id"]: v for v in payload.get("vendors", []) if isinstance(v, dict) and isinstance(v.get("id"), str)}
    for row in output["rows"]:
        problems = object_errors(row, ROW_FIELDS)
        if problems:
            errors.extend(problems)
            continue
        if row["id"] in seen or row["id"] not in vendors:
            errors.append("duplicate/unknown vendor")
        seen.add(row["id"])
        allowed = source_ids(vendors.get(row["id"], {}).get("documents", []))
        if set(row["evidence_ids"]) - allowed or len(row["evidence_ids"]) != len(set(row["evidence_ids"])):
            errors.append("unknown/duplicate evidence")
        if row["decision"] not in {"eligible", "ineligible", "undetermined"}:
            errors.append("invalid decision")
        if (row["status"] == "completed") != (row["decision"] in {"eligible", "ineligible"}):
            errors.append("row state/decision mismatch")
        if row["status"] == "needs_approval":
            errors.append("approval belongs to the request, not a row")
    if len(output["shortlist"]) != len(set(output["shortlist"])):
        errors.append("duplicate shortlist")
    eligible = {r.get("id") for r in output["rows"] if r.get("status") == "completed" and r.get("decision") == "eligible"}
    if set(output["shortlist"]) != eligible:
        errors.append("shortlist is not exactly eligible rows")
    return errors


def validate_judgment(response, profile, reference):
    if not isinstance(response, dict) or set(response) != {"verdict", "evidence_ids"}:
        raise ValueError("semantic response keys")
    if not isinstance(response["verdict"], str) or response["verdict"] not in VERDICTS:
        raise ValueError("semantic verdict")
    ids = response["evidence_ids"]
    if not string_list(ids) or set(ids) != {profile["id"], reference["id"]} or len(ids) != 2:
        raise ValueError("semantic evidence must identify the compared pair")
    return response["verdict"]
