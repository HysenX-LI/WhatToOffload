---
name: what-to-offload
description: Analyze an existing agent conversation, codebase, SOP, or workflow to find short-lived bounded subflows that should move into code or API runners, and map each atomic node to deterministic code, tools, Jev, LLMs, the current agent, or human review. Use when a user wants to reduce ongoing agent supervision, replace prompt-and-parse steps, or design and implement an offload plan. Do not use to build a scheduler, durable workflow platform, deployment system, or secret manager.
---

# WhatToOffload

Turn an existing workflow into a clearer division of labor. Keep the current agent where open-ended coordination is valuable; move bounded, testable work into ordinary software.

## Establish the operating mode

- **Analyze** is the default. Inspect evidence and recommend candidates without editing the target project.
- **Design** begins after the user selects a candidate. Produce the detailed workflow and implementation plan without editing the target project.
- **Implement** begins only when the user explicitly asks for implementation.
- If the user explicitly authorizes autonomous selection and implementation, choose the strongest candidate and continue, but keep required approval, live-API, and environment-choice stops.

Never treat a request to analyze or optimize as permission to modify code, call paid APIs, perform side effects, install the skill, or publish anything.

## Analyze the existing workflow

1. Inspect the conversation, repository, configuration, documents, and other materials already available to the agent. Do not make the user restate discoverable facts.
2. Identify missing facts that would materially change the workflow boundary or recommendation. Ask for those facts before recommending candidates.
3. Decompose the work into atomic nodes, then group related nodes into short-lived bounded subflows with clear input, output, termination, and failure boundaries.
4. Evaluate whether each node should stay in the current agent or move to an external runner. Separately choose the node's capability role and concrete implementation.
5. Present at most three leading offload candidates by default. Also identify important nodes that should remain in the current agent and explain why.

Read [references/short-lived-workflows.md](references/short-lived-workflows.md) before producing the candidate analysis. Copy or adapt [assets/templates/candidate-analysis.md](assets/templates/candidate-analysis.md) for the result.

Do not collapse the comparison into a fabricated precise score. Compare boundary clarity, agent supervision removed, replaceability, reuse, verifiability, cost and latency, implementation effort, uncertainty, and side-effect risk. Recommend an order using those dimensions.

## Design a selected subflow

At the start of detailed design, inspect the skills available in the current environment. Use skills that directly improve a workflow node or the artifact being analyzed. Do not maintain a speculative catalog of skill names.

For every node, record both layers:

- **Capability role:** deterministic code, existing tool or API, Jev, smaller LLM, stronger LLM or external agent, current agent, or human approval.
- **Concrete implementation:** the target project's language, function, provider, model, API, tool, or skill.

Choose the simplest executor that can meet the node's quality, safety, and testability requirements. This is a fitness decision, not a rigid cost-first ordering.

Read [references/executor-selection.md](references/executor-selection.md) when assigning executors. Read [references/safety-and-uncertainty.md](references/safety-and-uncertainty.md) whenever the workflow contains semantic uncertainty, external API calls, credentials, or side effects. Use [assets/templates/workflow-design.md](assets/templates/workflow-design.md) for the design.

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

Return the result envelope described in [assets/templates/result-envelope.json](assets/templates/result-envelope.json). Use these statuses consistently:

- `completed`: the bounded workflow produced its final result.
- `needs_input`: required source information is missing.
- `needs_review`: the input is complete, but a semantic judgment is too uncertain to continue safely.
- `needs_approval`: a side effect is ready but requires explicit approval.
- `failed`: execution failed and safe diagnostics are available.

## Keep Phase 1 bounded

Phase 1 supports short-lived workflows that complete in one invocation or return a caller-managed handoff state. It does not design or implement durable scheduling, background workers, cross-day waits, persistence, deployment, or a workflow control plane.

Use a relevant example only when it helps the current task:

- [examples/code-triage.md](examples/code-triage.md) for test-failure and issue triage.
- [examples/web-research.md](examples/web-research.md) for browser-assisted research and evidence handling.
- [examples/business-screening.md](examples/business-screening.md) for multi-label business intake and candidate scoring.

