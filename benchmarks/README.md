> Active public experiment: [Codex v2](codex_v2/README.md), using existing ChatGPT login only.
> [Current results and final-set status](codex_v2/RESULTS.md). The public_v1 API/$60 proposal below is historical, unexecuted and not authorized for this run.

# Public reproducible benchmark v1

Start with [public_v1/README.md](public_v1/README.md) for the runnable public supplier
case, independent answer tables, development/final splits, offline checks, isolated
execution/construction comparisons and generated reports. Its archived result is **offline software validation only**. For current Codex experiments and final-set exposure, use the v2 results linked above.

The historical microbenchmark harness now rejects missing/ill-typed fields,
invented citations and noncanonical approval actions. Summary generation cannot
replace protected fields, and expected non-completed outcomes can be correct.
Its v2 acceptance contract is stricter than the archived contract. Archived
measurements have not been rewritten or relabeled; future `--write-results` writes
to a fresh `.local/microbenchmark-v2-*` directory (or a new `--output-dir`).
Historical graphs are generated dynamically on new runs. These repairs concern
the shipped microbenchmark only, not the unavailable private long-task runner.

# Three-arm long-task benchmark (historical evidence)

The archived long-task comparison used the same local task through three independently measured paths:

| Arm | How the task runs | What is included |
| --- | --- | --- |
| `codex_only` | A fresh GPT-5.6 Sol high subagent receives the raw task and evidence | All task reasoning, local tools, temporary scripts and artifact creation |
| `codex_with_skill` | A fresh Sol high subagent receives the same task plus a task-specific Skill | Skill loading, agent reasoning, reusable deterministic helpers, local tools and artifacts |
| `whattooffload` | A prepared runner designed using WhatToOffload executes directly | Parsing, revision reconciliation, calculations, Jev judgments, low-confidence DeepSeek review, validation and deterministic artifacts |

The task covers 120 source documents, 24 suppliers and three separate projects. It requires cross-document evidence checks, quotation revision precedence, exact currency calculations, region/budget/deadline constraints, independent evidence interpretation, ranking, citations, exception queues and a 350–650-word report. It is a synthetic local task that was actually executed, not a production-client dataset.

![Three-arm long-task comparison](results/long-task-comparison.svg)

- [Full report, per-run measurements and limitations](results/long-task.md)
- [Machine-readable measurements](results/long-task.json)
- [Per-run CSV](results/long-task.csv)

## Comparable execution and acceptance

Each final arm runs three times. The Codex arms use fresh subagents with `gpt-5.6-sol` and `high` explicitly selected and verified in their runtime records. Both may use local tools and write scripts. The task Skill includes useful parsing/calculation helpers; it is not deliberately restricted to a prose-only prompt. Gold answers are absent from every executor workspace and never passed to providers.

A separate grader checks every output record, quote revision, rounded amount, reason, status, citation, shortlist and count. It also checks the narrative contract; the benchmark author reviews the prose. Formatting-equivalent lot labels are accepted. All runs use the same final grader. Sources, expected answers, responses and prose stay local.

The runner's final workflow is four sequential Jev batches, a DeepSeek review for uncertain judgments, and code-owned report assembly. The report includes actual fallback calls. The runner has no answer cache and is measured independently; its figures are not derived by subtracting a Codex review from another run.

## Cost boundary

Timing covers invocation through both output artifacts. Agent usage comes from the subagents' runtime token records, not an LLM estimate. Codex cumulative tokens include repeated tool-loop input and cached input; they are not unique task size. Jev and DeepSeek token counts remain separate because tokenizers differ.

Sol cost is a standard-rate API equivalent, not a ChatGPT plan invoice. Jev uses provider-reported cost. DeepSeek is calculated from actual cache/input/output usage with the dated applicable rate. Reasoning tokens already included in output are not billed twice. No-cost fields describe actual absent calls; unavailable measurements remain unknown.

One-time task-Skill and runner construction costs are separate from repeat execution. Their full cost was not independently metered, so this study cannot establish first-use total cost or a break-even point. Earlier failed runner attempts and their known provider costs are disclosed. Exploratory Astra measurements are excluded from the requested Sol comparison.

For repeated use, compare `setup + N × execution` for each prepared approach against `N × direct_execution`. A future Codex wrapper around the runner adds dispatch/return cost; this direct-software invocation does not measure that wrapper. Parent orchestration and grading are excluded for all three paths.

## Local-only workload

The workload, generator, exact task instructions, task Skill, reference answers, runner, evaluator and raw diagnostics live under the Git-ignored `.local/long-benchmark/`. Only an allowlist of measurements, workload dimensions, hashes and methodology is exported. No private fixture, source excerpt, output narrative, credential or local machine path belongs in the public result files.

This intentionally limits public reproducibility: readers can audit the published arithmetic and methodology but cannot rerun the exact private task from this repository. The same synthetic fixture was used during runner development, so the result is a development case study rather than a held-out generalization claim. Provider caches were uncontrolled, and Codex runs overlapped; the report shows ranges and makes no statistical guarantee from three repeats.

For the owner of this local workspace, offline checks are `python3 .local/long-benchmark/test_workflow.py`; result export is `python3 .local/long-benchmark/report.py --publish`. These local files are intentionally not shipped. Ordinary external-runner usage reads credentials from environment variables. Live calls must remain explicitly authorized.

---

# Historical microbenchmark

This benchmark compares the same three bounded synthetic workflows through two measured execution paths, with a third derived view:

- `codex_only`: GPT-5.6 Sol with high reasoning completes the raw task.
- `offloaded_verified`: Jev makes bounded judgments, deterministic code applies policy, DeepSeek writes the structured result, and a fresh GPT-5.6 Sol high invocation performs a thin contract check.
- `offloaded_runner_only`: the same measured offload execution with the optional Codex check removed. It is a lower-bound view, not an additional provider run, and excludes the host's small invocation/return envelope.

The fixtures cover code triage, supplied-page evidence synthesis, and business candidate screening. They do not fetch live pages or perform side effects. Each scenario and measured path runs three times; reports use medians and retain every per-run sanitized record.

## Historical results

![Token, latency, and cost comparison](results/comparison.svg)

- [Human-readable report](results/latest.md)
- [Machine-readable results](results/latest.json)

All 18 measured paths and all 9 derived runner-only outputs passed their scenario contracts in the recorded run. The main finding is a boundary condition: a truly bounded runner removed the per-task Sol invocation and was materially faster and cheaper, while adding a fresh Sol high verification to every result largely erased the benefit and sometimes made the path worse.

Cross-provider token totals are not treated as directly comparable because the tokenizers differ. The report therefore separates GPT-5.6 Sol main-agent tokens from Jev and DeepSeek external tokens. Codex USD values are API-price equivalents; ChatGPT plan execution consumes quota or credits rather than directly charging that amount.

Only three repetitions were requested. Sol prompt-cache hits varied across those runs, so its API-equivalent USD column is more volatile than the token and latency measurements. In particular, cost deltas for the optional verification path should be treated as directional rather than as a stable estimate.

## Run it

Real provider calls are intentionally not part of the default test suite. Set credentials only in the process environment, then opt into the live run:

```bash
export OPENROUTER_API_KEY='...'
export DEEPSEEK_API_KEY='...'
python3 -m benchmarks.benchmark --repetitions 3 --write-results
```

The benchmark uses the OpenRouter Decisions endpoint for `typesafe/jev-1.13`, DeepSeek's OpenAI-compatible Chat Completions endpoint with `deepseek-flash`, and the local Codex CLI with `gpt-5.6-sol` at high reasoning.

Raw Codex JSONL and provider diagnostics are written below `.local/benchmark-raw/`, which Git ignores. Committed results contain no credentials, authorization headers, or raw request headers.

The offline contract suite is:

```bash
python3 -m unittest benchmarks.test_benchmark -v
```

## Price snapshot

The report records a dated snapshot and source URLs for:

- [GPT-5.6 Sol API pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [Codex credit equivalents](https://learn.chatgpt.com/docs/pricing)
- [Jev 1.13 on OpenRouter](https://openrouter.ai/typesafe/jev-1.13/)
- [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing/)

Re-run or update the snapshot before using these figures for a budget decision. Provider prices, aliases, and alpha endpoints can change.

## Prospective v3 research

See [research_v3](research_v3/README.md) for the separate semantic-boundary and raw-workflow design studies, with blind model review, prospective freezes and architecture-neutral external acceptance. Historical artifacts remain unchanged.

The [completed v3 evidence](research_v3/RESULTS.md) separates prepared-execution savings from the limited raw-design observations, preserves reviewer timeouts and the failed customer receipt, and leaves the v2 no-observed-build-gain finding intact.
