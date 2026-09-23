import json
import sys

from .core import run


def _reject_nonstandard_constant(value):
    raise ValueError("non-standard JSON constant: {}".format(value))


def main():
    try:
        payload = json.load(sys.stdin, parse_constant=_reject_nonstandard_constant)
        result = run(payload)
    except Exception as exc:
        result = {
            "status": "failed",
            "summary": "Unhandled runner error.",
            "result": None,
            "required_action": None,
            "diagnostics": {"code": "unhandled_error", "message": str(exc)},
            "resume": None,
        }
        json.dump(result, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
        return 1
    json.dump(result, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0
