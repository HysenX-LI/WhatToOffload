# Research v3 evidence — two distinct questions

[Frozen protocol](PROTOCOL.md) · [semantic rules](SEMANTIC_RULES.md) · [full generated formal report](results/formal-1/report.md) · [all cases and phases](results/formal-1/report.json) · [round audit](results/round-audit.json) · [rerun commands](README.md)

All model invocations used ChatGPT-authenticated Codex, GPT-5.6 Sol/high. No independent paid-model API, API key, purchase, reset or automatic model switch was used. Billing and human rework are unknown.

## Semantic boundary and prepared execution

The original final-contact-partial-eligibility contract did not define how to establish the same project or claim. A reference describing slogans-only work does not by itself refute an unlinked broad capability claim. The new rule requires positive identity linkage for conflict; an unlinked bare denial is unclear, while affirmative other work is unrelated. [Historical audit](BOUNDARY_AUDIT.md).

Two independent-context Codex annotators agreed with every frozen new-final label. These are model annotations, not independent human labels. The separate [exposed historical-case diagnostic](results/historical-review-1/report.md) also classified e as unrelated under the new rules. That does not retroactively establish that the old model was wrong under its ambiguous prompt. Old gold, scores and freezes remain unchanged.

| Execution | Accepted cases | Median seconds | Input / cached / output tokens | Calls / tool items |
|---|---|---:|---|---|
| Direct Codex | 8/8 | 34.641 | 378,414 / 318,720 / 7,407 | 8 / 28 |
| Prepared code + bounded Codex | 8/8 | 9.457 | 73,281 / 46,592 / 172 | 8 / 0 |

The prepared path had 72.7% lower median latency and 80.6% fewer reported input tokens in this one run, with equal frozen-contract acceptance. This supports bounded workflow decomposition under Codex on this synthetic task. It does not measure Skill design gain, net lifetime savings, billing savings or another model’s advantage. One-time preparation investment is unknown.

Both arms had wrong eligibility releases 0/2 (also 0/6 of gold noneligible rows), conservative reviews 0/3, correct review recall 5/5, and correct approval handoff 1/1. Of each arm’s 8 tasks, 2 actually completed, 1 correctly awaited approval, and 5 correctly went to review. Completion among expected-completable tasks is 2/2; it is NOT universal business completion. Citations 32/32; omissions 0/8. All-review would fail resolved-case acceptance and completion.

## Raw-workflow design study

Each workflow has one independently constructed solution per arm, then the same withheld cases. Raw packets contained operational requests/SOPs/logs and a small existing stock helper, not node graphs or executor assignments. Both arms could choose keep_agent. No final input or gold was available during design/build/debug.

| Workflow / arm | Choice | Final acceptance | Design + build + explicit debug seconds | Construction calls | Model rubric /10 |
|---|---|---|---:|---:|---|
| stockroom / without_skill | implemented | 4/4 | 333.089 | 2 | 8 |
| stockroom / with_skill | implemented | 4/4 | 326.048 | 2 | 8 |
| release / without_skill | implemented | 4/4 | 479.847 | 3 | unknown — timeout |
| release / with_skill | implemented | 4/4 | 411.460 | 2 | unknown — timeout |
| customer / without_skill | keep_agent | 3/4 | 114.172 | 1 | 9 |
| customer / with_skill | keep_agent | 4/4 | 152.250 | 1 | 10 |

- **Stockroom:** equal acceptance and equal model-review total. Both chose software. Reviewers flagged unsupported input assumptions; the Skill candidate lost a feasibility point for a gap between planned and implemented tests, while the control lost a handoff point for stale/partial output handling. Reading resources is not credited as correct application.
- **Release:** equal final acceptance. The control first implemented a batch-array adapter despite the one-case external contract; both development smoke cases failed. One permitted debug invocation repaired that interface before final exposure. Its time/tokens and before/after smoke files remain visible. Both anonymous design reviews timed out at 120 seconds, so design-rating comparison is unavailable, not a tie or zero score.
- **Customer:** both correctly chose keep_agent. The control returned failed/no draft on c-approved because it added a requirement for concrete date and concession terms; the desk contract permitted a noncommittal topic-specific draft for approval. The Skill design produced such a draft and matched the frozen receipt contract. This is a local acceptance difference in one alternative scenario, with a one-point model handoff-rating difference. The evaluator does not fully measure relationship-sensitive writing quality; a human writing assessment was not performed.

These observations support a narrow descriptive gain on the customer receipt and different construction investment in release. They do not prove that WhatToOffload is generally better than ordinary Codex. The prior [detailed-spec construction study](../codex_v2/RESULTS.md) still reports **no observed incremental Skill construction gain**; it is not replaced or rescored.

Model ratings are separate from deterministic acceptance. Four of six design reviews returned scores; the two release review failures are retained without retries or imputation. Blinding removed identifiers/provenance lines, but writing style may reveal treatment. One reviewer per candidate, one build pair per workflow, three heterogeneous workflows, no significance test, uncontrolled cache/server variation. Different workflows are not repeated trials of one task.

## Effort, failures and measurement boundaries

| Workflow / arm | Construction input / cached / output | Execution seconds for final batch | Execution input / cached / output |
|---|---|---:|---|
| stockroom/without_skill | 253,517 / 214,656 / 14,138 | 0.472 | 0 / 0 / 0 |
| stockroom/with_skill | 262,280 / 219,136 / 13,897 | 0.432 | 0 / 0 / 0 |
| release/with_skill | 439,597 / 368,768 / 18,153 | 0.432 | 0 / 0 / 0 |
| release/without_skill | 436,819 / 365,952 / 21,634 | 0.442 | 0 / 0 / 0 |
| customer/without_skill | 65,411 / 56,832 / 5,025 | 67.255 | 65,684 / 45,696 / 2,585 |
| customer/with_skill | 109,825 / 91,264 / 6,150 | 50.087 | 65,899 / 57,728 / 1,691 |

The registered round used 47 Codex process invocations across development, formal work and the separate historical diagnostic, with 47 distinct observed context IDs. Experiment clock time was about 64.8 minutes (offline engineering excluded), within the registered 56-call/100-minute combined ceiling. Formal plus diagnostic used 39 of 48 calls and 50.8 of 80 minutes.

The main formal run used 37 calls and 157 CLI tool items. Known token subtotals are 2,392,098 input / 1,971,840 cached / 103,211 output. Usage is incomplete for its two timed-out model reviews; these are not full-round totals. Cached tokens are a subset of input, never added to it. Underlying internal model-request counts and billing remain unknown.

Execution wall includes workspace setup, CLI startup, context transfer, tools, return, parsing and the small in-process acceptance check. The construction table sums the design/implementation/explicit-debug event intervals: initial packet copying, independent smoke checks and candidate packaging sit outside those phase intervals but inside the entire-run clock. Internal debugging inside a build invocation cannot be separately timed/token-counted; it is included in build investment. Customer execution is one shared-context batch per arm, so individual case latency is unknown. Human rework is unknown.

[Development 1](results/dev-1/report.md) preserves a 300-second build timeout and unexecuted work. [Development 2](results/dev-2/report.md) used the remaining original development allowance, with fresh builders and a shorter build-scope prompt; construction and both execution paths passed. Total development: eight calls, including that failed invocation. [Partial interrupted-candidate script check](results/dev-partial-script-check.json) made zero model calls and does not relabel the interrupted build successful.

## Freeze, exposure and reproduction

Old v1 final is exposed regression. The first un-frozen v3 final draft was also retired after an offline stub countertest exercised three rows; its complete data/exposure record remains under data/semantic/exposed-draft. The replacement final changes actual judgment boundaries, including policy requirements, tuple identity and quoted claims. It was frozen before any final model exposure. [Current exposure log](EXPOSURE.jsonl) and [split provenance](data/SPLITS.json).

No final outcome changed implementation, prompts, rules, labels, thresholds or scoring. All candidate code was hashed before final exposure. New tests use development examples for executor countertests; gold auditing inspects schema/coverage independently. Main freeze and both old manifests still verify. Public result ledgers include the original calls.json in addition to exported per-call audits, enabling offline report regeneration without changing scores.

See [clean-copy validation](results/clean-copy-validation.json), [offline report reproduction](results/report-reproduction.json), and [commands](README.md). Raw request/response/tool logs remain in .local/research-v3-*; public results contain synthetic artifacts, every attempted result, review evidence, failures, immutable candidate hashes and anonymized event audits. No private long-task material or credentials are published.
