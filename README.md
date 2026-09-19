# WhatToOffload

[中文说明](README.zh-CN.md)

WhatToOffload is an Agent Skill for redesigning existing conversations, codebases, SOPs, and workflows as a clearer division of labor between an agent and ordinary software.

It finds atomic nodes, combines them into short-lived bounded subflows, and recommends the simplest executor that can reliably handle each node: deterministic code, an existing tool or API, Jev, a smaller model, a stronger model or agent, or human review.

## What it does

- Inspects available workflow evidence before asking the user to restate anything.
- Produces a small, ranked shortlist of offload candidates and a reasoned list of nodes to keep in the current agent.
- Separates *where a node runs* from *what capability executes it*.
- Expands a selected candidate into a workflow diagram, node table, interfaces, failure paths, approvals, and tests.
- Preserves the target project's stack and generates an importable runner plus a JSON CLI when implementation is authorized.
- Uses explicit result states for completion, missing input, semantic review, approval, and failure.

## What it is not

WhatToOffload is not a workflow runtime or hosting product. Phase 1 does not provide durable scheduling, background workers, persistence, deployment, queues, a dashboard, or secret management.

## Typical interaction

1. Ask WhatToOffload to analyze an existing workflow.
2. Review up to three offload candidates and the nodes recommended to remain with the agent.
3. Select a candidate to receive a detailed, renderer-independent workflow design.
4. Explicitly authorize implementation if you want the agent to change the target project.

The skill stops before external paid API calls and side effects unless those actions are explicitly approved.

## Phase 1 examples

- [Test-failure and issue triage](examples/code-triage.md)
- [Web research and evidence synthesis](examples/web-research.md)
- [Business intake and candidate screening](examples/business-screening.md)

Each example is intentionally compact: it includes an end-to-end specification and the key implementation shape, not a separate runnable application.

## Jev and TypeSafe

WhatToOffload identifies places where a narrow typed semantic judgment is a better fit than prompt-and-parse generation. Before implementing a Jev node, the agent must read the available `typesafe-ai` skill and the current [TypeSafe documentation](https://docs.typesafe.ai/llms.txt). Code remains responsible for control flow, deterministic rules, side effects, and uncertainty routing.

## Repository layout

- `SKILL.md` is the single skill entry point.
- `references/` contains detailed Phase 1 design guidance loaded only when relevant.
- `assets/templates/` contains human-readable specifications and JSON protocol examples.
- `examples/` contains three cross-domain walkthroughs.
- `agents/openai.yaml` contains optional Codex-facing metadata without changing the generic skill instructions.

## Roadmap

Future phases may explore durable asynchronous workflows, additional professional-skill routing, and richer workflow visualization. Those capabilities are intentionally not specified or claimed in Phase 1.

## Project status

This repository currently contains the source skill only. It is not installed automatically and does not configure a GitHub remote. External API probes are opt-in and require explicit authorization.

During development on 2026-09-20, an explicitly authorized synthetic contract probe verified Choice, Noul, and Score results through the OpenRouter Decisions API and strict JSON generation through DeepSeek's OpenAI-compatible Chat Completions API. The repository contains no credentials or provider-specific runtime configuration, and this probe is evidence of compatibility rather than a permanent service guarantee.
