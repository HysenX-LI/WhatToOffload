# WhatToOffload

[中文说明](README.zh-CN.md)

WhatToOffload is an Agent Skill for redesigning existing conversations, codebases, SOPs, and workflows as a clearer division of labor between an agent and ordinary software.

It finds atomic nodes, combines them into short-lived bounded or durable asynchronous subflows, and recommends the simplest executor that can reliably handle each node: deterministic code, an existing tool or API, Jev, a smaller model, a stronger model or agent, or human review.

## Why not stop at a Skill?

Many agent workflows take a mature, repeatable task and document it as a Skill. This improves consistency, but the agent still has to load the instructions, carry the working context, invoke every tool, follow the intermediate state, and make each routine decision every time the task runs.

WhatToOffload uses a Skill for a different purpose: to help the agent move a stable normal path out of its own loop. Once the boundary is understood and tested, the task can be packaged as an ordinary runner that combines deterministic scripts and tools, a configured model API, and the Jev API. The runner completes the bounded workflow without an agent continuously supervising it; the agent returns only for missing input, low-confidence review, approval, failure, or genuinely open-ended decisions.

The goal is therefore not merely to teach an agent how to repeat the work. It is to turn mature work into callable software and reduce the agent context, tokens, elapsed time, and attention consumed across repeated runs. The Skill remains the analysis and design layer; the generated runner owns routine execution.

## What it does

- Inspects available workflow evidence before asking the user to restate anything.
- Produces a small, ranked shortlist of offload candidates and a reasoned list of nodes to keep in the current agent.
- Separates *where a node runs* from *what capability executes it*.
- Expands a selected candidate into a workflow diagram, node table, interfaces, failure paths, approvals, and tests.
- Recognizes when a flow must survive restarts or wait for timers, events, delayed retries, input, review, or approval, then designs the durable state and recovery boundary.
- Uses contract-driven TDD: define observable behavior first, confirm a meaningful failing test, implement the smallest slice, and keep the workflow protected by regression tests.
- Preserves the target project's stack and generates an importable runner plus a JSON CLI when implementation is authorized.
- Uses explicit result states for completion, missing input, semantic review, approval, and failure.

## What it is not

WhatToOffload is not a workflow runtime or hosting product. Phase 2 can design and integrate with an existing or deliberately selected durable runtime, but the Skill does not itself provide scheduling, workers, persistence, deployment, queues, a dashboard, or secret management.

## Typical interaction

1. Ask WhatToOffload to analyze an existing workflow.
2. Review up to three offload candidates, their short-lived or durable workflow class, and the nodes recommended to remain with the agent.
3. Select a candidate to receive a detailed, renderer-independent workflow design.
4. Explicitly authorize implementation if you want the agent to change the target project.

The skill stops before external paid API calls and side effects unless those actions are explicitly approved.

## Workflow modes

- **Phase 1 — short-lived bounded:** completes in one invocation or returns a caller-managed handoff.
- **Phase 2 — durable asynchronous:** survives process lifetimes and resumes from persisted events, timers, retries, or human action owned by an external runtime.

Phase 2 keeps activity results separate from workflow lifecycle. Activities use `completed`, `needs_input`, `needs_review`, `needs_approval`, or `failed`; durable snapshots use `active`, `waiting`, `completed`, `failed`, or `cancelled`, with a separate wait reason.

## Examples

- [Test-failure and issue triage](examples/code-triage.md)
- [Web research and evidence synthesis](examples/web-research.md)
- [Business intake and candidate screening](examples/business-screening.md)
- [Durable multi-day vendor review](examples/durable-vendor-review.md)

The three short-lived walkthroughs now describe multi-stage tasks with conflicting evidence, partial results, exception handling and complete deliverables. They explain the workflow; the larger benchmark task and its implementation stay local.

## Jev and TypeSafe

WhatToOffload identifies places where a narrow typed semantic judgment is a better fit than prompt-and-parse generation. Before implementing a Jev node, the agent must read the available `typesafe-ai` skill and the current [TypeSafe documentation](https://docs.typesafe.ai/llms.txt). Code remains responsible for control flow, deterministic rules, side effects, and uncertainty routing.

The configured reference stack for upgraded model-assisted runners is Jev (`typesafe/jev-1.13`) plus DeepSeek-V4.1-Flash, whose official API model ID is [`deepseek-flash`](https://api-docs.deepseek.com/quick_start/pricing/). Jev supplies bounded typed judgments; DeepSeek handles complex extraction, review, and missing-evidence recovery. Code owns tools, control flow, validation, and final status.

## Long-horizon website information processing

A real private website task compares **Sol high directly**, **Sol high + the original task Skill**, and a **WhatToOffload workflow using Jev + DeepSeek-V4.1-Flash**. Evaluation measures entity coverage, available-field recall, asserted-field precision, evidence and strict acceptance alongside time and model cost.

The latest three-path comparison reports completion scores of **92.8 / 96.4 / 89.2**, with execution-model costs of **$4.5361 / $3.5562 / $0.2095** respectively. Read the [full report and measurement method](benchmarks/results/website-long-horizon.md).

![Website task comparison](benchmarks/results/website-long-horizon-comparison.svg)

One execution per path is reported on this case. All three recovered all reference entities, but **none passed strict acceptance**. Completion and strict acceptance are separate measures; the comparison does not establish a general success rate or unseen-case generalization. Codex costs are API-equivalent estimates from actual session tokens; setup and debugging costs are excluded.

The task, source identities, raw materials, reference answers, execution outputs and implementation remain local. Only sanitized metrics, opaque hashes and generic methodology are public.

## Historical synthetic batch-task comparison

The primary benchmark compares **Codex**, **Codex + a task-specific Skill**, and **a WhatToOffload-designed runner** on the same local workload: 120 source documents, 24 candidates and three projects, with revised quotations, evidence conflicts, missing inputs, calculations, rankings and a complete report.

The two Codex paths use fresh **GPT-5.6 Sol high** subagents. The Skill path includes reusable deterministic helpers. The third path is an independently measured runner combining code, Jev and DeepSeek review for uncertain cases. Each final path runs three times under the same acceptance contract.

![Three-arm long-task comparison](benchmarks/results/long-task-comparison.svg)

These are prepared **repeat-execution** measurements. Full one-time construction cost is unknown and is not treated as zero; development failures and their measured provider costs are disclosed. The task was used during runner development, so this is a synthetic development case study, not a held-out or production performance guarantee.

The exact task, input documents, reference answers, task Skill, runner and raw logs stay local and Git-ignored. The repository publishes only sanitized measurements, hashes and methodology. Read the [full comparison](benchmarks/results/long-task.md) and [measurement method](benchmarks/README.md). The earlier small-example results remain available as historical microbenchmarks, not as evidence for this three-arm comparison.

## Repository layout

- `SKILL.md` is the single skill entry point.
- `references/` contains short-lived, durable, executor-selection, safety, and test-driven implementation guidance loaded only when relevant.
- `assets/templates/` contains human-readable specifications and JSON protocol examples.
- `examples/` contains multi-stage cross-domain walkthroughs for both workflow modes.
- `agents/openai.yaml` contains optional Codex-facing metadata without changing the generic skill instructions.
- `benchmarks/` contains the long-task measurement report and historical microbenchmark tooling; the new long-task workload and implementation stay under Git-ignored `.local/`.

## Phase 2 boundary

The durable playbook covers state ownership, versioning, events, timers, retries, idempotency, human waits, recovery, cancellation, observability, and runtime fit. It prefers infrastructure the target project already operates. When no runtime exists, selection remains an explicit architecture decision rather than silently generating a home-grown scheduler.

Future work may add more professional-skill routing, richer visualization, and further validated durable examples without turning this repository into a runtime product.

## Project status

This repository contains the source skill only. It is not installed automatically and does not provision or operate workflow infrastructure. External API probes are opt-in and require explicit authorization.

During development on 2026-09-20, an explicitly authorized synthetic contract probe verified Choice, Noul, and Score results through the OpenRouter Decisions API and strict JSON generation through DeepSeek's OpenAI-compatible Chat Completions API. The repository contains no credentials or provider-specific runtime configuration, and this probe is evidence of compatibility rather than a permanent service guarantee.
