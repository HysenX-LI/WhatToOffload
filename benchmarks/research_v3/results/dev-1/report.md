# Research v3 — dev

Mode: real_codex. Stop reason: Codex_build_timeout.

Reported totals: 4 Codex calls, 21 CLI tool items; input/cache/output known subtotals 112795 / 68608 / 6120. Usage complete: False. Billing and human rework: unknown.

## Semantic boundary — deterministic external acceptance

| Arm | Accepted | Coverage | Wrong release | Conservative review | Correct review | Approval handoff | Business completion | Median seconds |
|---|---|---|---|---|---|---|---|---|
| direct | 0/1 | 0/1 | 0/0 | 0/1 | 0/0 | 0/0 | 0/1 | unknown |
| bounded | 0/1 | 0/1 | 0/0 | 0/1 | 0/0 | 0/0 | 0/1 | unknown |

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
| stockroom/without_skill | None | 0/2 | 0/2 | 96.766 | 300.036 | not applicable / not executed | unknown | None |

Model rubric is separate from executable acceptance; one candidate per arm/workflow, not repeated independent builds. Script runnability applies only when software is selected. Keep-agent without a runner is a valid outcome. Debug inside implementation is included in build investment and has unknown separate duration/tokens.

## Failures and unexecuted work

- stockroom/without_skill/implementation: Codex_build_timeout

Unexecuted required entries: 3. See report.json for every case, denominator, reason, phase, annotation rationale and missing measurement.

## Inference limits

These are synthetic small-sample Codex observations. No significance, universal Skill advantage, billing saving, Jev, DeepSeek or cheaper-model conclusion follows. Reviewers are models; author labels are not independently human validated. Final labels and scoring are not changed after exposure. The older detailed-spec study still reports no observed Skill construction gain.
