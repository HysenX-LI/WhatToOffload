"""Structural checks only. No gold labels or business decision rules."""
STATES = frozenset({"completed", "needs_input", "needs_review", "needs_approval", "failed"})


def string_list(value):
    return isinstance(value, list) and all(isinstance(x, str) and x.strip() for x in value)


def object_errors(value, fields):
    if not isinstance(value, dict):
        return ["output must be an object"]
    errors = []
    if set(value) != set(fields):
        errors.append("required/unknown fields: " + ",".join(sorted(set(value) ^ set(fields))))
    for key, kind in fields.items():
        item = value.get(key)
        valid = {"str": lambda: isinstance(item, str) and bool(item.strip()),
                 "strings": lambda: string_list(item),
                 "bool": lambda: type(item) is bool,
                 "objects": lambda: isinstance(item, list) and all(isinstance(x, dict) for x in item)}[kind]()
        if not valid:
            errors.append("invalid type/value: " + key)
    if "status" in fields and (not isinstance(value.get("status"), str) or value["status"] not in STATES):
        errors.append("invalid status")
    return errors


def source_ids(value):
    found = set()
    if isinstance(value, dict):
        if isinstance(value.get("id"), str):
            found.add(value["id"])
        for child in value.values():
            found.update(source_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(source_ids(child))
    return found


HISTORICAL_FIELDS = {"status": "str", "scenario_id": "str", "decision": "str",
                     "summary": "str", "evidence_ids": "strings", "next_actions": "strings"}
APPROVAL_ACTION = "Request human approval before any vendor outreach or purchase."
