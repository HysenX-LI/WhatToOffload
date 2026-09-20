# Long-horizon website information processing

One private live-web case is measured through two one-run Codex baselines and caller-specified workflow repetitions. Task identities, domains, records, source text, expected values, raw outputs, traces, and implementation details remain local.

**Completion and success are different.** Completion score measures recovered coverage; strict success additionally requires precision, evidence, conflict recording, resolved required pages, and saved artifacts.

| Execution path | Run | Executor status | Time | Model cost | Completion score | Strict success |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| Codex (Sol high) | 1 | completed | 455.5s | $2.144702 | 100.0/100 | pass |
| Codex + original Skill (Sol high) | 1 | completed | 467.1s | $1.710218 | 94.6/100 | fail |
| WhatToOffload workflow (Jev + DeepSeek) | 1 | needs_review | 258.5s | $0.080566 | 97.9/100 | fail |

The two Codex baselines have n=1 each. They are reused measured baselines, not rerun estimates.

The original manifest declared 3 sequential same-case repetitions. An explicit user amendment cancelled 2 unstarted repetitions before any API call or output, replacing them with a separate held-out evaluation. This report therefore contains the sole effective same-case repetition and makes no three-run aggregate claim. The retained run is reported regardless of outcome.

The reporter verified the effective run set, cancellation artifact absence, per-run freeze metadata, grading protocol, and frozen runner hash; it did not select a winner.

Original manifest SHA-256: `5a4e44e9091c4b066a8e4771d22a8508bb6faa138701f6c55bb8729c0fcb89a5`; amendment SHA-256: `434dd4524aaf45a9cc6333cc3c5721d6bf00e8e9d3aa44ec036ec945bba2bf32`; frozen runner SHA-256: `cf9a0a50d0aa0597c627aa0af8bef580b6c7393c55759bcde8924f05ec9acda2`.

One final workflow run was explicitly supplied, so no mean, range, or success rate is reported.

## Quality detail

| Execution path | Run | Entity recall | Available-field recall | Asserted-field precision | Evidence coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Codex (Sol high) | 1 | 100.0% | 100.0% | 100.0% | 100.0% |
| Codex + original Skill (Sol high) | 1 | 100.0% | 91.1% | 100.0% | 100.0% |
| WhatToOffload workflow (Jev + DeepSeek) | 1 | 100.0% | 96.4% | 98.2% | 98.1% |

## Retained workflow history

Every executed workflow attempt other than the explicitly supplied final run remains in the history, including interrupted or ungradable development attempts. Explicitly cancelled, unstarted repetitions are recorded in the manifest amendment above.

| Attempt | Workflow generation | Executor status | Time | Known cost | Completion score | Strict success |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | historical Jev-only | completed | 49.6s | $0.001253 | 0.0/100 | fail |
| 2 | historical Jev-only | failed | 135.1s | ≥$0.002038 | 0.0/100 | fail |
| 3 | historical Jev-only | completed | 144.4s | ≥$0.002390 | 78.6/100 | fail |
| 4 | upgraded Jev + DeepSeek | failed | 35.3s | $0.000677 | 0.0/100 | fail |
| 5 | upgraded Jev + DeepSeek | failed | 30.8s | $0.004603 | 0.0/100 | fail |
| 6 | upgraded Jev + DeepSeek | needs_review | 358.6s | ≥$0.128834 | 30.5/100 | fail |
| 7 | upgraded Jev + DeepSeek | needs_review | 350.0s | $0.095482 | 97.9/100 | fail |

## Model and measurement boundary

The upgraded workflow requests Jev `typesafe/jev-1.13` for bounded typed judgments and DeepSeek-V4.1-Flash through the official `deepseek-flash` API alias for complex extraction, review, and missing-evidence recovery. Returned provider model IDs are retained in the JSON. The DeepSeek alias is documented mapping, not a pinned model version. Code owns retrieval tools, control flow, validation, and completion status; the executor makes no additional Codex semantic calls.

Jev cost uses provider-reported `usage.cost`. DeepSeek cost uses actual prompt cache-hit, prompt cache-miss, and completion tokens at the Sunday off-peak snapshot of $0.003 / $0.15 / $0.60 per million tokens. Reasoning tokens are already included in completion and are not billed twice. Missing usage on a failed call produces a lower bound.

Known provider spend across retained and final workflow attempts: **at least $0.315843**. Setup and repair were not fully metered.

Executor latency includes the fixed-code host web-tool bridge. Parent dispatch, setup and repair, grading, local compute, and human review are excluded. Search-tool fees are unknown, matching the baseline measurement boundary.

## Workflow generations and repairs

Historical published attempts were Jev-only. Upgraded development and final runs use the declared Jev + DeepSeek stack; the report never retroactively relabels historical attempts.

- **Historical Jev-only:** The initial bounded workflow relied on narrower deterministic retrieval and parsing, and could report completion despite unresolved coverage. The upgraded workflow separates complex extraction and recovery from typed verification, and makes unresolved coverage part of executor status.
- **Upgraded Jev + DeepSeek:** Development runs exposed generic grounding, section-context, decision-size, truncated-response, and citation-source canonicalization failure modes. The frozen runner self-grounds discovered URLs, preserves source sections, splits oversized Jev decisions deterministically, retries truncated DeepSeek JSON, merges complementary snippets for the same canonical source URL, and cites an outbound account through its referring evidence page without changing the value; Jev still verifies ownership.

## Limits and privacy

- The two Codex baselines each have one measured run.
- Workflow repairs and reruns use the same private case; this is not a held-out evaluation.
- Every caller-specified final run is reported; no winner is selected.
- Live web content, provider caches, web search, and tool environments are uncontrolled.
- Unknown failed-call charges make the reported workflow cost a lower bound, never zero.
- Completion score and strict success are separate: a high completion score is not a pass.

The workflow was repaired and rerun on the same case; it is not a held-out evaluation. Public export uses a fixed metric allowlist and contains no case identity, domain, person, contact value, private field label, source excerpt, expected answer, or raw trace.

Files: [JSON](website-long-horizon.json), [CSV](website-long-horizon.csv).
