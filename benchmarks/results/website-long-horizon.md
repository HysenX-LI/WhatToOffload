# 网站信息处理长程任务 / Long-horizon website information processing

One real, private, multi-page website task; three execution paths. Exact task instructions, source identities, page content, outputs, Skill/workflow code and traces remain local. This report publishes measurements only.

**Completion is evaluated independently of executor status. Lower cost on an incomplete result is not a successful-task saving.**

![Cost, duration and completion](website-long-horizon-comparison.svg)

| Execution path | Time | Model cost (USD) | Entity recall | Available-field recall | Asserted-field precision | Completion score | Strict pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Codex (Sol high) | 455.5s | $2.144702 | 100.0% | 100.0% | 100.0% | 100.0/100 | yes |
| Codex + original Skill (Sol high) | 467.1s | $1.710218 | 100.0% | 91.1% | 100.0% | 94.6/100 | no |
| WhatToOffload workflow (revised) | 144.4s | ≥$0.002390 | 100.0% | 64.3% | 94.7% | 78.6/100 | no |

The revised workflow row is a same-case development result, not an untouched first attempt. The complete initial-attempt history is below. Each agent arm ran once with a fresh **gpt-5.6-sol / high** subagent. No median or significance claim is made.

## Completion assessment

A separately authored reference covers 9 target entities and seven requested data fields per entity. The task requires navigation, extraction, source reconciliation and saved evidence. The direct agent receives the goal and output contract without procedural steps; the Skill arm also reads an authentic historical task Skill. Both may browse, search and write scripts. The workflow receives the same starting identity and target scope, with no reference answers or extracted roster supplied.

- Entity recall and precision measure missing, extra and duplicate records.
- Available-field recall counts correctly recovered reference values, including fields on omitted records. Asserted-field precision penalizes unsupported or wrong populated values.
- Completion score = 40% × entity recall + 60% × available-field recall. Precision and evidence are reported separately; the score alone cannot establish success.
- Strict pass requires complete entity coverage with no extras, ≥95% available-field recall, 100% asserted-field precision, ≥95% evidence coverage, preserved source conflicts, no unresolved required pages and all requested saved artifacts.
- Reference-unavailable fields may remain null with explicit checks/status. Verified additional findings are added to the reference and all paths are rescored uniformly. Future or reported dates count only when explicitly identified as such.

| Path | Correct / available fields | Supported / correct fields | Explicit statuses for unavailable fields |
| --- | ---: | ---: | ---: |
| Codex (Sol high) | 56/56 | 56/56 | 7/7 |
| Codex + original Skill (Sol high) | 51/56 | 51/51 | 7/7 |
| WhatToOffload workflow (revised) | 36/56 | 36/36 | 6/6 |

## Earlier workflow attempts

| Attempt | Executor status | Time | Known model cost | Entities returned | Strict pass |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | completed | 49.6s | $0.001253 | 0 | no |
| 2 | failed | 135.1s | ≥$0.002038 | 0 | no |

The first attempt returned a completion status while omitting the required records. A generic section-parsing repair was then made. The next attempt failed during a provider connection; the revised measurement added bounded transport retries. None of these attempts was discarded or reclassified as a successful task. The revised run still omits available fields, includes two unsupported assignments and lacks one required output artifact.

## Cost and measurement boundary

Codex amounts are standard-rate API equivalents from actual runtime usage, including cached input and output; reasoning tokens are already included in output and are not double-counted. They are not ChatGPT subscription invoices. Jev amounts come from provider-reported usage.cost. A **≥** amount is a known subtotal: a transport-failed request returned no usage, so its charge is unknown rather than assumed zero.

| Path | Codex input / cached / output tokens | External input / output tokens | Unpriced request attempts |
| --- | ---: | ---: | ---: |
| Codex (Sol high) | 3,105,248 / 2,942,336 / 15,806 | 0 / 0 | 0 |
| Codex + original Skill (Sol high) | 2,316,494 / 2,194,944 / 17,302 | 0 / 0 | 0 |
| WhatToOffload workflow (revised) | 0 / 0 / 0 | 56,914 / 7,248 | 3 |

Known provider spend across all workflow attempts: **at least $0.005682**. Full preparation and repair cost is unknown. There is no first-task total or break-even estimate.

Execution time runs from executor invocation to saved artifacts. Shared setup, reference construction, parent orchestration and grading are excluded for all arms. The workflow is invoked directly by software; a future Codex dispatch/review wrapper adds cost and is not measured here. Search-tool fees and local compute are also outside the model-cost column.

## Limits and privacy

- One private case, one run per agent arm; no statistical inference or public task reproduction.
- Revised workflow was repaired on this case; all earlier execution attempts are retained.
- Live web content, provider caches, web-search behavior and tool environments were not controlled.
- No end-to-end saving is claimed for a path that fails the common acceptance gate.
- Costs are model-execution components: Codex API equivalents and Jev reported charges. Search-tool fees, local compute, setup and human review costs are not measured.
- Reference additions are independently source-checked and applied uniformly; the reference review is by agents and the benchmark author, not an external audit.

Only aggregate metrics, opaque hashes and this generic methodology are published. No case name, source domain, person, source text, task prompt, reference table, raw trace or private implementation is included.

Files: [JSON](website-long-horizon.json), [CSV](website-long-horizon.csv). Price snapshot (2026-09-20): [Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [Jev](https://openrouter.ai/typesafe/jev-1.13).
