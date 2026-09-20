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

Each example is intentionally compact: it includes an end-to-end specification and the key implementation shape, not a separate runnable application.

## Jev and TypeSafe

WhatToOffload identifies places where a narrow typed semantic judgment is a better fit than prompt-and-parse generation. Before implementing a Jev node, the agent must read the available `typesafe-ai` skill and the current [TypeSafe documentation](https://docs.typesafe.ai/llms.txt). Code remains responsible for control flow, deterministic rules, side effects, and uncertainty routing.

## Live benchmark

The repository includes a reproducible, opt-in comparison across the three short-lived examples. Each measured path ran three times with real GPT-5.6 Sol high, Jev 1.13 through OpenRouter, and DeepSeek Flash calls.

![Live token, latency, and cost comparison](benchmarks/results/comparison.svg)

The recorded synthetic run found that the bounded Jev + DeepSeek runner-only path reduced sequential median latency by 52.5–75.0% and API-equivalent cost by 95.0–99.5%, while all outputs passed the scenario contracts. A fresh Sol high verification on every offloaded result largely erased those gains, exposing an important design rule: keep routine validated outputs outside the strong-agent loop and reserve re-entry for review conditions.

Read the [methodology and limitations](benchmarks/README.md) or inspect the [full result table](benchmarks/results/latest.md). Live calls remain opt-in and require explicit authorization.

## Repository layout

- `SKILL.md` is the single skill entry point.
- `references/` contains short-lived, durable, executor-selection, safety, and test-driven implementation guidance loaded only when relevant.
- `assets/templates/` contains human-readable specifications and JSON protocol examples.
- `examples/` contains compact cross-domain walkthroughs for both workflow modes.
- `agents/openai.yaml` contains optional Codex-facing metadata without changing the generic skill instructions.
- `benchmarks/` contains offline contract tests, synthetic fixtures, an opt-in live runner, and sanitized result artifacts.

## Phase 2 boundary

The durable playbook covers state ownership, versioning, events, timers, retries, idempotency, human waits, recovery, cancellation, observability, and runtime fit. It prefers infrastructure the target project already operates. When no runtime exists, selection remains an explicit architecture decision rather than silently generating a home-grown scheduler.

Future work may add more professional-skill routing, richer visualization, and further validated durable examples without turning this repository into a runtime product.

## Project status

This repository contains the source skill only. It is not installed automatically and does not provision or operate workflow infrastructure. External API probes are opt-in and require explicit authorization.

During development on 2026-09-20, an explicitly authorized synthetic contract probe verified Choice, Noul, and Score results through the OpenRouter Decisions API and strict JSON generation through DeepSeek's OpenAI-compatible Chat Completions API. The repository contains no credentials or provider-specific runtime configuration, and this probe is evidence of compatibility rather than a permanent service guarantee.
