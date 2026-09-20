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

## Load supporting resources progressively

Do not pre-load every reference, template, or example when this skill is activated. Start with this `SKILL.md`, inspect the available evidence, and determine the current operating mode and workflow class first.

- During initial analysis, read only the short-lived or durable playbook that matches the candidate being evaluated. Read both only when the evidence genuinely contains both workflow classes or the classification itself is ambiguous.
- When recommending concrete replacements, also read the replacement procedure in [references/executor-selection.md](references/executor-selection.md#work-through-a-replacement). Use steps 1–3 during analysis; complete steps 4–7 for a selected design and its authorized implementation.
- Open [assets/templates/candidate-analysis.md](assets/templates/candidate-analysis.md) only when producing a candidate-analysis deliverable.
- During detailed design, open exactly the matching short-lived or durable design template, plus only the executor or safety references required by the selected nodes.
- Read [references/test-driven-workflows.md](references/test-driven-workflows.md) only after a candidate reaches detailed design or implementation and code or executable workflow behavior is in scope.
- Treat files under `assets/` as output resources, not background instructions. Do not inspect an asset merely because it exists.
- Read an example only after the domain and pattern are known, and only when that example materially helps the current task. Never load all examples for orientation.
- Load `typesafe-ai` and its routed documentation only when a selected node is actually being designed or implemented with Jev.

## Analyze the existing workflow

1. Inspect the conversation, repository, configuration, documents, and other materials already available to the agent. Do not make the user restate discoverable facts.
2. Identify missing facts that would materially change the workflow boundary or recommendation. Ask for those facts before recommending candidates.
3. Decompose the work into atomic nodes, then group related nodes into subflows with clear input, output, termination, and failure boundaries. Classify each subflow as short-lived or durable asynchronous.
4. Identify the specific behavior being replaced, the context it currently relies on, and the capability the replacement must preserve. Evaluate whether it should stay in the current agent or move to an external runner. Separately choose its capability role and concrete implementation; state the benefit, capability loss, and evidence behind each proposed replacement.
5. Present at most three leading offload candidates by default. Also identify important nodes that should remain in the current agent and explain why.

Read [references/short-lived-workflows.md](references/short-lived-workflows.md) for candidates that complete in one invocation or return a caller-managed handoff. Read [references/durable-async-workflows.md](references/durable-async-workflows.md) when a candidate crosses process lifetimes, waits for timers or external events, resumes after human action, or needs persisted retries. When it is time to present candidates, copy or adapt [assets/templates/candidate-analysis.md](assets/templates/candidate-analysis.md).

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

Apply the [replacement procedure](references/executor-selection.md#work-through-a-replacement): observe the current behavior → define acceptance → compare executors → specify evidence → bound recovery → test the substitution → measure the complete path. For each material replacement, record what is gained, what flexibility or coverage may be lost, how failure is detected, and what evidence would justify retaining or reversing it. Do not assume every workflow should be a code → Jev → LLM cascade.

Read [references/executor-selection.md](references/executor-selection.md) when assigning executors. Read [references/safety-and-uncertainty.md](references/safety-and-uncertainty.md) whenever the workflow contains semantic uncertainty, external API calls, credentials, or side effects. For a short-lived design, open only [assets/templates/workflow-design.md](assets/templates/workflow-design.md). For a durable design, read [references/durable-async-workflows.md](references/durable-async-workflows.md) and open only [assets/templates/durable-workflow-design.md](assets/templates/durable-workflow-design.md).

Show the connection between nodes with the best visualization capability available in the environment, then provide the node table. Keep the underlying workflow description renderer-independent. If no visualization capability is available, use a compact text diagram or simple Mermaid as a fallback.

Do not edit the target project after presenting the design. Wait for an explicit implementation request unless the user already granted autonomous implementation.

## Design for test-driven implementation

For a selected workflow, define observable acceptance behavior before production implementation. Include normal results, uncertainty routes, missing input, provider failure, approval stops, and side-effect containment. If the target is an existing implementation, plan characterization tests before changing behavior.

When implementation is authorized, read [references/test-driven-workflows.md](references/test-driven-workflows.md) and work in small red-green-refactor slices:

1. Add the smallest meaningful test and run it to confirm that it fails for the intended missing behavior.
2. Implement only enough workflow or activity code to make that test pass.
3. Refactor while keeping the relevant suite green, then repeat for the next behavior.

Do not claim a TDD cycle when the test was never observed failing. Preserve the target project's test framework and conventions. Test public contracts and state transitions rather than private implementation structure.

For Jev and LLM nodes, combine deterministic contract tests with representative semantic cases. Assert downstream policy outcomes, valid uncertainty routing, and schema invariants; do not lock tests to exact prose or one permanent probability. Use provider fakes by default and keep live probes behind explicit confirmation.

## Use Jev deliberately

Use Jev for narrow, typed semantic judgments over supplied state, not for open-ended planning, prose generation, tool execution, or control flow. Code owns deterministic rules, branching, composition, side effects, and confidence gates.

When code and Jev cover the normal path, reserve stronger models for explicit exceptions. Do not require an LLM before or after every Jev decision. Follow the [exception-routing guidance](references/executor-selection.md#keep-stronger-models-on-an-explicit-exception-branch) and measure escalation frequency alongside quality and latency.

Before designing Jev questions or writing Jev code:

1. Find and read the complete `typesafe-ai` skill available in the current environment.
2. Follow that skill's routing to the current official TypeSafe documentation and the relevant primitive or cookbook.
3. If the skill is unavailable, state the limitation and read the live official documentation starting at <https://docs.typesafe.ai/llms.txt>. Do not invent version-dependent API details.

Do not copy the TypeSafe manual into this skill. This skill decides *where* Jev fits; `typesafe-ai` and the live docs decide *how* to implement it.

## Implement only after authorization

- Preserve the target project's language, package manager, conventions, and test stack.
- Begin with the test-first slice defined in the approved design. For legacy behavior without coverage, add characterization tests before refactoring it.
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

Do not read examples during initial skill loading. After the workflow class and domain are known, read at most the closest relevant example when it materially helps the task:

- [examples/code-triage.md](examples/code-triage.md) for test-failure and issue triage.
- [examples/web-research.md](examples/web-research.md) for browser-assisted research and evidence handling.
- [examples/business-screening.md](examples/business-screening.md) for multi-label business intake and candidate scoring.
- [examples/durable-vendor-review.md](examples/durable-vendor-review.md) for an event-driven, multi-day review with model judgments and human approval.
