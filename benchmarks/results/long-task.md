# Local long-workflow benchmark

Three independent execution arms, three final repetitions each. All raw tasks, private inputs, labels, task Skill, runner and execution logs stay local. This is a synthetic development workload, not a held-out or independently audited study.

![Three-arm comparison](long-task-comparison.svg)

| Path | Runs passing | Median time | Range | Median Codex tokens | Median cost (USD) | Cost range |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Codex | 3/3 | 209.26s | 171.11–237.10s | 453,761 | $0.515262 | $0.428371–$0.628228 |
| Codex + task Skill | 3/3 | 102.14s | 75.54–114.94s | 468,282 | $0.376757 | $0.300965–$0.388373 |
| WhatToOffload runner | 3/3 | 5.92s | 5.82–6.07s | 0 | $0.000766 | $0.000745–$0.000822 |

Codex costs are standard-rate API equivalents calculated from actual subagent usage, including tool-loop input, cached input, output and any reasoning tokens already included in output. They are not ChatGPT subscription invoices. External cost combines Jev reported cost and DeepSeek usage priced at the applicable weekend off-peak rate. Cross-provider tokens are separated below.

## Per-run measurements

| Path | Run | Seconds | Input / cached / output Codex tokens | Jev input / output | DeepSeek input / output | USD | Rows correct | Brief words | Pass |
| --- | ---: | ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| Codex | 1 | 209.26 | 474,837 / 409,600 / 10,172 | 0 / 0 | 0 / 0 | $0.628228 | 24/24 | 396 | pass |
| Codex | 2 | 171.11 | 425,402 / 396,288 / 7,670 | 0 / 0 | 0 / 0 | $0.428371 | 24/24 | 365 | pass |
| Codex | 3 | 237.10 | 442,175 / 412,544 / 11,586 | 0 / 0 | 0 / 0 | $0.515262 | 24/24 | 358 | pass |
| Codex + task Skill | 1 | 102.14 | 477,924 / 447,872 / 3,870 | 0 / 0 | 0 / 0 | $0.376757 | 24/24 | 426 | pass |
| Codex + task Skill | 2 | 75.54 | 381,543 / 356,352 / 2,883 | 0 / 0 | 0 / 0 | $0.300965 | 24/24 | 382 | pass |
| Codex + task Skill | 3 | 114.94 | 463,332 / 434,432 / 4,950 | 0 / 0 | 0 / 0 | $0.388373 | 24/24 | 458 | pass |
| WhatToOffload runner | 1 | 5.82 | 0 / 0 / 0 | 11,642 / 1,279 | 613 / 402 | $0.000822 | 24/24 | 494 | pass |
| WhatToOffload runner | 2 | 5.92 | 0 / 0 / 0 | 11,642 / 1,279 | 613 / 368 | $0.000745 | 24/24 | 494 | pass |
| WhatToOffload runner | 3 | 6.07 | 0 / 0 / 0 | 11,642 / 1,279 | 613 / 402 | $0.000766 | 24/24 | 494 | pass |

## Recurring execution comparison

Compared with Codex, the final prepared runner uses 99.9% less API-equivalent cost and 97.2% less median wall time on this workload.
Compared with Codex + task Skill, the final prepared runner uses 99.8% less API-equivalent cost and 94.2% less median wall time on this workload.

## Development and setup accounting

The final runner was repaired on this same development fixture before its three measured final runs. Three earlier attempts are retained below: one exhausted the DeepSeek thinking budget without producing a brief; two exposed evidence-classification and report-length failures. These are not silently counted as successful tasks or included as final-run repetitions.

| Development attempt | Execution | Contract | Seconds | External USD |
| --- | --- | --- | ---: | ---: |
| 1 | failed | FAIL | 42.33 | $0.006915 |
| 2 | completed | FAIL | 7.12 | $0.001341 |
| 3 | completed | FAIL | 7.61 | $0.001121 |

Known runner development API spend: **$0.009377**. Final runner API spend: **$0.002333**. Combined measured runner-provider spend: **$0.011710**. This is only the measured provider component of setup and execution.

Full one-time Skill/runner construction cost and human review time were not separately metered and are **unknown, not zero**. Exploratory Astra runs were excluded when the user specified Sol high; they are not part of the formal model comparison. No measured first-task total, net lifetime savings or break-even claim is made.

`total_A(N) = N × run_A`; `total_B(N) = setup_B + N × run_B`; `total_C(N) = setup_C + N × run_C`.

Break-even against either baseline requires the incremental setup cost as well as a positive per-run saving. Supply a measured setup cost before estimating it.

## Quality, privacy and limitations

- Every final result is checked against the same independently authored expected table, including all 24 records, currency rounding, quote precedence, status, reasons, citations, rankings and counts. Report checks cover length and required facts; author review checks prose. This is not an independent human quality assessment.
- The fixed input contains 120 source documents plus a task, manifest and policy (73,035 bytes), 24 candidates and three projects. Its SHA-256 is recorded in the JSON; documents and labels are withheld.
- A reference-answer half-cent rounding bug was corrected to the predeclared half-up rule before final runner measurement. The narrative checker was also corrected to accept equivalent labels such as Lot A and lot-a, and checks cent-accurate prices. Inputs and executor outputs were not changed to make them pass.
- A and B use fresh Sol high subagents with no conversation fork. Both can use local tools and scripts; B also gets a task-specific Skill and deterministic helpers. Those helpers contain no semantic labels. The runner shares the same deterministic policy helper with B.
- C is the actual independently invoked prepared runner, not subtraction of a Codex verification call. It makes four sequential Jev batches, routes low-confidence cases to DeepSeek, and assembles the final report deterministically. It reads no reference answers and has no response cache.
- Low-confidence semantic fallback calls, including their reasoning tokens and latency, are included. Normal expected missing-input/review outcomes count as correctly completed review records, not automatic procurement decisions.
- The common boundary starts at executor invocation and ends with both artifacts ready. C is called directly by software; its per-run Codex tokens are zero. A future Codex dispatch/return wrapper would add cost and must be measured separately. Parent orchestration and artifact-grading costs are excluded for every arm.
- Codex jobs overlapped in time; cache state was not controlled, and repetitions reused the same frozen input. Latency and API-equivalent cost are observations with visible ranges, not a randomized sequential trial or a statistical guarantee.
- Public artifacts are allowlisted metrics and hashes only. Private local fixtures prevent independent reproduction from this repository alone. This dataset was used during runner development; a new held-out set is needed to test generalization.

Price references: [Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/), [Jev](https://openrouter.ai/typesafe/jev-1.13). Snapshot: 2026-09-20.
