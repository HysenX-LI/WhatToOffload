# Long-horizon website information processing

This report compares three execution paths on one private website information-processing task using the same task goal and quality rubric. It presents the latest measured workflow configuration. Task identities, sources, reference answers, implementation and raw artifacts remain local.

| Path | Time | Model cost | Completion / 100 | Field recall | Field precision | Strict acceptance |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Codex / Sol high | 788.7s | $4.536140 | 92.8 | 88.0% | 100.0% | fail |
| Codex + original Skill / Sol high | 763.3s | $3.556231 | 96.4 | 94.0% | 100.0% | fail |
| WhatToOffload / Jev + DeepSeek-V4.1-Flash | 495.6s | $0.209468 | 89.2 | 82.0% | 95.3% | fail |

![Website task comparison](website-long-horizon-comparison.svg)

## Measurement and models

Both Codex paths use independent **GPT-5.6 Sol high** subagents. The direct path receives the task goal; the Skill path also receives the original task Skill. The WhatToOffload workflow uses **Jev (`typesafe/jev-1.13`) + DeepSeek-V4.1-Flash (`deepseek-flash` API alias)**. Jev handles typed verification; DeepSeek handles complex extraction and evidence recovery; code controls retrieval, bounded retries, validation and saved artifacts. The API alias is not a pinned model version.

All executor turns are included in time and token measurements, including the same output-contract clarification for both baselines. Executors did not receive reference answers or prior execution outputs. All paths are scored against the same independently adjudicated reference.

Completion is `100 × (0.4 × entity recall + 0.6 × available-field recall)`. Strict acceptance requires complete and precise membership, at least 95% field recall, 100% asserted-field precision, at least 95% evidence coverage, correct conflict handling, required-page resolution and saved artifacts. Missing available values count against recall.

All three paths recovered all reference entities. Correct available fields were 44/50, 47/50 and 41/50 respectively. The Skill path also lacked one supporting citation; the workflow asserted two unsupported values. **All three executions failed strict acceptance.** Completion and cost must be read together; lower execution cost alone does not establish a successful-task saving.

## Cost boundary

Jev cost uses returned `usage.cost`. DeepSeek uses measured cache-hit, cache-miss and completion tokens at the 2026-09-20 off-peak [pricing snapshot](https://api-docs.deepseek.com/quick_start/pricing/): $0.003, $0.15 and $0.60 per million tokens respectively. Codex cost is an API-equivalent estimate from actual session tokens, not a subscription invoice: $4/M uncached input, $0.4/M cached input, $5/M cache writes and $20/M output. Reasoning tokens are included in output and are not charged twice.

Time covers executor invocation through saved artifacts, including the host web-tool bridge. Workflow construction and debugging, parent orchestration, reference construction and grading, local compute and search-tool fees are excluded. Provider failures without returned usage cannot be priced. These figures measure execution-model spend, not total ownership cost.

## Scope and provenance

One execution per path is reported on one private case. Live web content, provider caches and tool availability are uncontrolled. This comparison does not establish a statistical success rate or generalization to unseen cases.

Only sanitized measurements, generic methodology and opaque artifact hashes are published. The JSON includes token measurements, provider cost breakdowns and reference, grader, runner and result hashes.

[JSON](website-long-horizon.json) · [CSV](website-long-horizon.csv)
