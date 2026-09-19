# Example: test-failure and issue triage

This compact example shows how a repeatedly supervised debugging intake can become a short-lived runner. It does not attempt to fix the code.

## Before

An agent repeatedly reads test output, removes noise, guesses the failure family, searches the repository, and writes the same investigation handoff. The loop consumes conversation context even when no open-ended debugging is required.

## Proposed boundary

```text
test command result + repository metadata
  -> parse deterministic signals
  -> retrieve likely files and recent changes
  -> classify the failure family
  -> compose a bounded investigation brief
  -> completed | needs_review | failed
```

Input:

```json
{
  "command": "pytest tests/test_checkout.py -q",
  "exit_code": 1,
  "stdout": "...",
  "stderr": "AssertionError: expected status 200, got 409",
  "changed_files": ["src/checkout.py", "tests/test_checkout.py"]
}
```

Output: a structured failure family, evidence, likely files, and next checks. Applying a fix remains with the current agent because it requires repository-wide reasoning and authorization to edit.

## Node map

| Node | Location | Capability role | Concrete implementation | Why |
| --- | --- | --- | --- | --- |
| Validate invocation | Runner | Deterministic code | Existing project language | Required fields and size limits are exact rules |
| Parse failures | Runner | Deterministic code | Test-framework parser plus safe fallback | Stack frames, exit codes, and file paths should not require a model |
| Gather repository evidence | Runner | Existing tool | Read-only search and VCS metadata | Uses authoritative local state |
| Classify failure family | Runner | Jev | Choice over defined categories | Requires semantic interpretation but has a bounded answer surface |
| Draft investigation brief | Runner | Smaller LLM | OpenAI-compatible chat completion | Produces concise prose from already selected evidence |
| Decide or implement a repair | Current agent | Stronger reasoning and tools | Host agent | Scope varies and edits require explicit authorization |

Example Choice options might be `product_regression`, `test_regression`, `environment`, `flaky_or_timing`, and `insufficient_evidence`. Read `typesafe-ai` and current docs before implementing the request.

## Key implementation shape

```python
def triage_failure(payload, dependencies):
    parsed = dependencies.test_parser.parse(payload)
    if not parsed.failures:
        return completed({"classification": "no_test_failure", "evidence": []})

    evidence = dependencies.repo_reader.gather(parsed.paths, payload["changed_files"])
    judgment = dependencies.jev.classify_failure(parsed, evidence)

    if judgment.choice == "insufficient_evidence" or judgment.confidence < dependencies.review_threshold:
        return needs_review(
            summary="Failure family is ambiguous.",
            result={"probabilities": judgment.probabilities, "evidence": evidence},
        )

    brief = dependencies.llm.write_brief(
        classification=judgment.choice,
        evidence=evidence,
    )
    return completed({
        "classification": judgment.choice,
        "confidence": judgment.confidence,
        "evidence": evidence,
        "investigation_brief": brief,
    })
```

The importable function and JSON CLI consume the same payload and return the common result envelope.

## Representative tests

- Syntax or import error is parsed without a model.
- Clear assertion mismatch selects `product_regression` or `test_regression` according to supplied evidence.
- Competing categories with a flat distribution return `needs_review`.
- Missing logs return `needs_input`.
- Provider failure returns sanitized `failed`; no raw authorization header or repository secret is captured.
- No test auto-applies a repair.

