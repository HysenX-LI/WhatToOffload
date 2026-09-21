# Research v3 — formal

Mode: real_codex. Stop reason: None.

Reported totals: 37 Codex calls, 157 CLI tool items; input/cache/output known subtotals 2392098 / 1971840 / 103211. Usage complete: False. Billing and human rework: unknown.

## Semantic boundary — deterministic external acceptance

| Arm | Accepted | Coverage | Wrong release | Conservative review | Correct review | Approval handoff | Business completion | Median seconds |
|---|---|---|---|---|---|---|---|---|
| direct | 8/8 | 8/8 | 0/2 | 0/3 | 5/5 | 1/1 | 2/2 | 34.641 |
| bounded | 8/8 | 8/8 | 0/2 | 0/3 | 5/5 | 1/1 | 2/2 | 9.457 |

Two independent-context Codex model annotations (not human labels):

| Case | Author | Reviewer 1 | Reviewer 2 |
|---|---|---|---|
| sem-f01 | conflict | conflict | conflict |
| sem-f02 | unrelated | unrelated | unrelated |
| sem-f03 | unclear | unclear | unclear |
| sem-f04 | corroborated | corroborated | corroborated |
| sem-f05 | conflict | conflict | conflict |
| sem-f06 | unclear | unclear | unclear |
| sem-f07 | corroborated | corroborated | corroborated |
| sem-f08 | unclear | unclear | unclear |

## Raw-workflow study — each pair separately

| Workflow / arm | Mode | Accepted | Coverage | Design s | Build s | Debug s | Execute s | Model rubric /10 |
|---|---|---|---|---|---|---|---|---|
| stockroom/without_skill | implemented | 4/4 | 4/4 | 137.861 | 195.228 | not applicable / not executed | 0.472 | 8 |
| stockroom/with_skill | implemented | 4/4 | 4/4 | 192.697 | 133.352 | not applicable / not executed | 0.432 | 8 |
| release/with_skill | implemented | 4/4 | 4/4 | 172.799 | 238.661 | not applicable / not executed | 0.432 | None |
| release/without_skill | implemented | 4/4 | 4/4 | 136.447 | 169.491 | 173.909 | 0.442 | None |
| customer/without_skill | keep_agent | 3/4 | 4/4 | 114.172 | not applicable / not executed | not applicable / not executed | 67.255 | 9 |
| customer/with_skill | keep_agent | 4/4 | 4/4 | 152.25 | not applicable / not executed | not applicable / not executed | 50.087 | 10 |

Model rubric is separate from executable acceptance; one candidate per arm/workflow, not repeated independent builds. Script runnability applies only when software is selected. Keep-agent without a runner is a valid outcome. Debug inside implementation is included in build investment and has unknown separate duration/tokens.

## Failures and unexecuted work

- release/without_skill/review: RuntimeError:failed_bounded_invocation:Codex_semantic_timeout
- release/with_skill/review: RuntimeError:failed_bounded_invocation:Codex_semantic_timeout
- customer/without_skill/execute/c-approved: draft_topic_missing, mismatch:status; None

Unexecuted required entries: 0. See report.json for every case, denominator, reason, phase, annotation rationale and missing measurement.

## Inference limits

These are synthetic small-sample Codex observations. No significance, universal Skill advantage, billing saving, Jev, DeepSeek or cheaper-model conclusion follows. Reviewers are models; author labels are not independently human validated. Final labels and scoring are not changed after exposure. The older detailed-spec study still reports no observed Skill construction gain.
