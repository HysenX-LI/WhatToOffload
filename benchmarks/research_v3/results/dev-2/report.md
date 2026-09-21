# Research v3 — dev

Mode: real_codex. Stop reason: None.

Reported totals: 4 Codex calls, 22 CLI tool items; input/cache/output known subtotals 396658 / 313728 / 14966. Usage complete: True. Billing and human rework: unknown.

Annotation evidence is reused from development run research-v3-dev-1. Its failed build remains in that separate report; the totals here cover only this run.
## Semantic boundary — deterministic external acceptance

| Arm | Accepted | Coverage | Wrong release | Conservative review | Correct review | Approval handoff | Business completion | Median seconds |
|---|---|---|---|---|---|---|---|---|
| direct | 1/1 | 1/1 | 0/0 | 0/1 | 0/0 | 0/0 | 1/1 | 30.623 |
| bounded | 1/1 | 1/1 | 0/0 | 0/1 | 0/0 | 0/0 | 1/1 | 8.715 |

Two independent-context Codex model annotations (not human labels):

| Case | Author | Reviewer 1 | Reviewer 2 |
|---|---|---|---|
| link-other | unrelated | unrelated | unrelated |
| link-same | conflict | conflict | conflict |
| partial | unclear | unclear | unclear |
| denied | conflict | conflict | conflict |
| no-link | unclear | unclear | unclear |
| other-work | unrelated | unrelated | unrelated |
| support | corroborated | corroborated | corroborated |
| vague | unclear | unclear | unclear |

## Raw-workflow study — each pair separately

| Workflow / arm | Mode | Accepted | Coverage | Design s | Build s | Debug s | Execute s | Model rubric /10 |
|---|---|---|---|---|---|---|---|---|
| stockroom/without_skill | implemented | 2/2 | 2/2 | 143.64 | 196.18 | not applicable / not executed | 0.248 | None |

Model rubric is separate from executable acceptance; one candidate per arm/workflow, not repeated independent builds. Script runnability applies only when software is selected. Keep-agent without a runner is a valid outcome. Debug inside implementation is included in build investment and has unknown separate duration/tokens.

## Failures and unexecuted work

No observed failures.

Unexecuted required entries: 0. See report.json for every case, denominator, reason, phase, annotation rationale and missing measurement.

## Inference limits

These are synthetic small-sample Codex observations. No significance, universal Skill advantage, billing saving, Jev, DeepSeek or cheaper-model conclusion follows. Reviewers are models; author labels are not independently human validated. Final labels and scoring are not changed after exposure. The older detailed-spec study still reports no observed Skill construction gain.
