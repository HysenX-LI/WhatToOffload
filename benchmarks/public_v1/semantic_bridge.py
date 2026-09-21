"""Copied to isolated candidate workspace. The host answers one pair at a time."""
import json
import sys


def judge(domain, profile, reference):
    print(json.dumps({"semantic_request": {"domain": domain, "profile": profile, "reference": reference}}), flush=True)
    response = json.loads(sys.stdin.readline())
    if "error" in response:
        raise RuntimeError("semantic bridge failed")
    return response["answer"]
