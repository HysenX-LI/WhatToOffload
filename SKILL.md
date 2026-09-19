---
name: what-to-offload
description: Analyze an existing agent conversation, codebase, SOP, or workflow to find bounded or durable asynchronous subflows that should move into software, and map each atomic node to deterministic code, tools, Jev, LLMs, the current agent, or human review. Use when a user wants to reduce ongoing agent supervision, replace prompt-and-parse steps, or design and implement an offload plan. This skill designs integrations with workflow runtimes; it does not itself host, schedule, deploy, or manage secrets for them.
---

# WhatToOffload

Turn an existing workflow into a clearer division of labor. Keep the current agent where open-ended coordination is valuable; move contractible, testable work into ordinary software. A candidate may finish in one invocation or continue through durable state, events, timers, and human waits owned by an external runtime.

## Establish the operating mode

- **Analyze** is the default. Inspect evidence and recommend candidates without editing the target project.
- **Design** begins after the user selects a candidate. Produce the detailed workflow and implementation plan without editing the target project.
- **Implement** begins only when the user explicitly asks for implementation.
- If the user explicitly authorizes autonomous selection and implementation, choose the strongest candidate and continue, but keep required approval, live-API, and environment-choice stops.

Never treat a request to analyze or optimize as permission to modify code, call paid APIs, perform side effects, install the skill, or publish anything.

## Analyze the existing workflow

1. Inspect the conversation, repository, configuration, documents, and other materials already available to the agent. Do not make the user restate discoverable facts.
2. Identify missing facts that would materially change the workflow boundary or recommendation. Ask for those facts before recommending candidates.
3. Decompose the work into atomic nodes, then group related nodes into subflows with clear input, output, termination, and failure boundaries. Classify each subflow as short-lived or durable asynchronous.
4. Evaluate whether each node should stay in the current agent or move to an external runner. Separately choose the node's capability role and concrete implementation.
5. Present at most three leading offload candidates by default. Also identify important nodes that should remain in the current agent and explain why.

Read [references/short-lived-workflows.md](references/short-lived-workflows.md) for candidates that complete in one invocation or return a caller-managed handoff. Read [references/durable-async-workflows.md](references/durable-async-workflows.md) when a candidate crosses process lifetimes, waits for timers or external events, resumes after human action, or needs persisted retries. Copy or adapt [assets/templates/candidate-analysis.md](assets/templates/candidate-analysis.md) for the result.

Do not collapse the comparison into a fabricated precise score. Compare boundary clarity, agent supervision removed, replaceability, reuse, verifiability, cost and latency, implementation effort, uncertainty, and side-effect risk. Recommend an order using those dimensions.

## Choose the workflow class

- **Short-lived bounded:** one invocation can reach a terminal result or return state that the immediate caller owns. Use the ordinary workflow design template.
- **Durable asynchronous:** progress must survive worker or agent restarts, or the workflow waits for a timer, callback, external event, delayed retry, human input, review, or approval. Use the durable design playbook and template.

Elapsed time alone is not the deciding factor. A long computation can remain a bounded job; a two-minute approval wait may require durable state. Do not disguise a durable workflow as repeated agent polling.

WhatToOffload is still a design and implementation skill, not a control plane. For a durable candidate, identify the existing runtime that will own state, scheduling, event delivery, and recovery. If none exists, present the missing runtime as an architecture decision; do not silently invent a scheduler, database, queue, or deployment.

## Design a selected subflow

At the start of detailed design, inspect the skills available in the current environment. Use skills that directly improve a workflow node or the artifact being analyzed. Do not maintain a speculative catalog of skill names.

For every node, record both layers:

- **Capability role:** deterministic code, existing tool or API, Jev, smaller LLM, stronger LLM or external agent, current agent, or human approval.
- **Concrete implementation:** the target project's language, function, provider, model, API, tool, or skill.

Choose the simplest executor that can meet the node's quality, safety, and testability requirements. This is a fitness decision, not a rigid cost-first ordering.

Read [references/executor-selection.md](references/executor-selection.md) when assigning executors. Read [references/safety-and-uncertainty.md](references/safety-and-uncertainty.md) whenever the workflow contains semantic uncertainty, external API calls, credentials, or side effects. Use [assets/templates/workflow-design.md](assets/templates/workflow-design.md) for a short-lived design. For a durable design, first read [references/durable-async-workflows.md](references/durable-async-workflows.md), then use [assets/templates/durable-workflow-design.md](assets/templates/durable-workflow-design.md).

Show the connection between nodes with the best visualization capability available in the environment, then provide the node table. Keep the underlying workflow description renderer-independent. If no visualization capability is available, use a compact text diagram or simple Mermaid as a fallback.

Do not edit the target project after presenting the design. Wait for an explicit implementation request unless the user already granted autonomous implementation.

## Use Jev deliberately

Use Jev for narrow, typed semantic judgments over supplied state, not for open-ended planning, prose generation, tool execution, or control flow. Code owns deterministic rules, branching, composition, side effects, and confidence gates.

Before designing Jev questions or writing Jev code:

1. Find and read the complete `typesafe-ai` skill available in the current environment.
2. Follow that skill's routing to the current official TypeSafe documentation and the relevant primitive or cookbook.
3. If the skill is unavailable, state the limitation and read the live official documentation starting at <https://docs.typesafe.ai/llms.txt>. Do not invent version-dependent API details.

Do not copy the TypeSafe manual into this skill. This skill decides *where* Jev fits; `typesafe-ai` and the live docs decide *how* to implement it.

## Implement only after authorization

- Preserve the target project's language, package manager, conventions, and test stack.
- When a standalone Python runner is genuinely needed and the target has no Python environment choice, ask whether to use `uv`. If the user declines or does not answer, use the available Python environment. Treat this as an environment detail, not a product feature.
- Expose core runner logic as an importable function and a JSON CLI unless the target project provides a more appropriate equivalent interface.
- Use environment-based configuration for OpenAI-compatible LLM calls: base URL, model, and API key. Do not bind the design to OpenRouter or another provider.
- Never write credentials into source, examples, logs, diagnostics, or returned state.
- Run static and mock validation by default. Obtain explicit confirmation immediately before any real Jev, LLM, or other paid/external API call.
- For durable work, preserve the target project's existing workflow engine, queue, database, event bus, deployment model, and observability conventions. Add adapters and workflow definitions rather than a parallel home-grown control plane.
- If the target has no durable runtime, stop at an explicit runtime-selection decision unless the user authorizes choosing and implementing one. Record operational ownership, hosting, retention, and cost implications before implementation.

Return the result envelope described in [assets/templates/result-envelope.json](assets/templates/result-envelope.json). Use these statuses consistently:

- `completed`: the bounded workflow produced its final result.
- `needs_input`: required source information is missing.
- `needs_review`: the input is complete, but a semantic judgment is too uncertain to continue safely.
- `needs_approval`: a side effect is ready but requires explicit approval.
- `failed`: execution failed and safe diagnostics are available.

These statuses describe a node or bounded runner result. They do not describe the lifecycle of a durable workflow. For durable designs, also adapt [assets/templates/async-workflow-snapshot.json](assets/templates/async-workflow-snapshot.json): use `active`, `waiting`, `completed`, `failed`, or `cancelled` for lifecycle and record a separate wait reason. Do not expose secrets, raw authorization material, or unnecessary source content in persisted snapshots.

## Keep the product boundary clear

Phase 1 covers short-lived bounded workflows. Phase 2 adds a playbook for designing and, when explicitly authorized, integrating durable asynchronous workflows into an existing or deliberately selected runtime. Neither phase makes this Skill a scheduler, worker host, persistence layer, deployment system, operations console, or secret manager.

Use a relevant example only when it helps the current task:

- [examples/code-triage.md](examples/code-triage.md) for test-failure and issue triage.
- [examples/web-research.md](examples/web-research.md) for browser-assisted research and evidence handling.
- [examples/business-screening.md](examples/business-screening.md) for multi-label business intake and candidate scoring.
- [examples/durable-vendor-review.md](examples/durable-vendor-review.md) for an event-driven, multi-day review with model judgments and human approval.
