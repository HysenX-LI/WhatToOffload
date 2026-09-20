# Example: test-failure and issue triage

This example follows a release-gate investigation across multiple test jobs, repository changes, and product requirements. The runner prepares a decision-ready investigation package; applying repairs remains a separate task.

## Worked scenario: a release candidate with several failures

A checkout release has twelve CI jobs. Four jobs fail, one reports a timeout before tests start, and two failures repeat the same checkout assertion on different platforms. The release owner needs a consolidated brief, an evidence-backed classification for each distinct failure, likely owners, and the next checks before deciding whether to ship.

The input pack contains the job manifest, structured test results, raw log excerpts, a diff against the last passing commit, current checkout requirements, an ownership map, and the previous three runs. One test still expects the old response format; another exposes an implementation change that conflicts with the current requirement. A dependency download timeout is unrelated to product behavior. A payment callback fails intermittently, but the supplied history is too short to establish flakiness.

The work is deliberately more than classifying one error message:

1. Check that logs, test results and diffs refer to the same commit. Return missing evidence explicitly when they do not.
2. Extract failed tests, stack frames, setup failures and exit codes. Preserve the original job and source IDs.
3. Group repeated manifestations by test identity and normalized error signature. Keep both platform observations attached to the group.
4. Join each group to changed files, current requirements and historical observations. A matching filename alone is not proof of causation.
5. Ask bounded semantic questions about the competing explanations. Evaluate uncertainty per failure group, not just once for the release.
6. Map supported findings to owners and investigation actions with deterministic rules. Do not invent an owner when the ownership map has no match.
7. Draft a release brief and a machine-readable queue. A source ID must resolve to supplied evidence, and each failure must appear exactly once in the queue.
8. Return completed groups together with unresolved groups. A missing log for one job must not erase useful results from the others.

| Evidence pattern | Expected handling | What stays with the agent |
| --- | --- | --- |
| Same assertion on two platforms; implementation contradicts current requirement | One product-regression group, two job references, responsible file owner | Investigate and repair the implementation |
| Old assertion conflicts with an explicit revised requirement | Test-regression group with requirement and test references | Decide and implement the test update |
| Download timeout before collection | Environment group; do not describe it as a failed product test | Retry or infrastructure coordination if authorized |
| Intermittent callback failure with limited history | Review queue with competing explanations | Decide which additional evidence to collect |

The deliverables are `triage.json`, a grouped investigation queue, and a brief that identifies unresolved release risks. The runner must not report that a release is safe merely because it successfully generated those artifacts.

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

- Multiple jobs with the same root signature produce one group without losing platform evidence.
- A stale requirement or mismatched commit cannot support a confident diagnosis.
- The number of accounted-for jobs equals the supplied manifest, including setup failures and incomplete jobs.
- Every cited file, requirement and log ID resolves to the input pack; absent ownership routes to review.
- Syntax or import error is parsed without a model.
- Clear assertion mismatch selects `product_regression` or `test_regression` according to supplied evidence.
- Competing categories with a flat distribution return `needs_review`.
- Missing logs return `needs_input`.
- Provider failure returns sanitized `failed`; no raw authorization header or repository secret is captured.
- No test auto-applies a repair.
