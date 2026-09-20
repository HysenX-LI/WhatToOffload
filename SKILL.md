---
name: what-to-offload
description: Analyze an existing agent conversation, codebase, SOP, or workflow to find bounded or durable asynchronous subflows that should move into software, and map each atomic node to deterministic code, tools, Jev, LLMs, the current agent, or human review. Use when a user wants to reduce ongoing agent supervision, replace prompt-and-parse steps, or design and implement an offload plan. This skill designs integrations with workflow runtimes; it does not itself host, schedule, deploy, or manage secrets for them.
license: MIT
---

# WhatToOffload

Move stable, contractible work out of repeated agent supervision while keeping open-ended coordination, changing goals, and accountable decisions with the current agent or a human. A candidate may finish in one invocation or continue through durable state owned by an external runtime.

## Choose the operating mode

- **Analyze** by default: inspect evidence and recommend at most three candidates without editing the target project.
- **Design** after the user selects a candidate: define the workflow and implementation plan without editing the target project.
- **Implement** only after explicit authorization. Autonomous selection plus implementation is allowed only when the user explicitly grants both.

Analysis or optimization is not permission to edit code, install the skill, publish data, make live calls, deploy, or perform side effects.

Keep a lightweight handoff across modes: stable candidate/design IDs, analysis/design versions, input or case-set version, frozen quality boundary, explicitly accepted trade-offs, and exact authorization scope. Use the supplied templates rather than inventing a state-management system.

## Load resources progressively

Start with this file and the available evidence. Do not preload every reference, asset, or example.

- For analysis, read [short-lived workflows](references/short-lived-workflows.md) or [durable asynchronous workflows](references/durable-async-workflows.md), whichever matches the candidate. Read both only when classification is genuinely ambiguous.
- When comparing replacements, use steps 1–3 of [executor selection](references/executor-selection.md); finish the procedure for a selected design or authorized implementation.
- Open [candidate-analysis.md](assets/templates/candidate-analysis.md) only when producing the analysis deliverable.
- For design, open exactly [workflow-design.md](assets/templates/workflow-design.md) or [durable-workflow-design.md](assets/templates/durable-workflow-design.md), plus only the references required by selected nodes.
- Read [safety and uncertainty](references/safety-and-uncertainty.md) for model judgment, credentials, external calls, or side effects.
- Read [workflow observability](references/workflow-observability.md) for multi-stage retrieval, semantic decisions, fallback, or measured quality that needs causal diagnosis.
- Read [test-driven workflows](references/test-driven-workflows.md) only when detailed design or implementation makes executable behavior relevant.
- Read at most the closest example after the domain and workflow class are known.

Treat files under `assets/` as output resources, not background instructions.

## Analyze the workflow

Inspect discoverable conversations, code, SOPs, configuration, tests, traces, and outputs; do not ask the user to restate them. Ask only for missing facts that would materially change a boundary or recommendation.

Decompose the work into atomic nodes, then group nodes into subflows with explicit inputs, outputs, termination, and failures. For each candidate identify:

- the behavior and context being replaced;
- the capability and quality boundary that must survive;
- the proposed execution location, capability role, and concrete implementation;
- expected benefit, capability or coverage loss, failure detection, recovery, and smallest fair comparison;
- work that should remain in the current agent or human process.

Compare boundary clarity, supervision removed, replaceability, reuse, verifiability, cost and latency, implementation effort, uncertainty, and side-effect risk. Do not fabricate a precise aggregate score.

## Classify the workflow

- **Short-lived bounded:** one invocation reaches a terminal result or returns state owned by its immediate caller.
- **Durable asynchronous:** correctness depends on state surviving restarts or waiting for a timer, callback, delayed retry, external event, human input, review, or approval.

Elapsed time alone does not decide the class. Do not disguise durable waiting as repeated agent polling. For durable work, identify the existing owner of persistence, scheduling, delivery, and recovery. If none exists, stop at an architecture decision rather than inventing a scheduler, database, queue, or deployment.

## Select executors and design

Record both layers for every material node:

- **Capability role:** deterministic code, existing tool or API, Jev, smaller LLM, stronger LLM or external agent, current agent, or human approval.
- **Concrete implementation:** target language, function, provider, model, API, tool, or skill.

Choose the simplest executor that meets quality, safety, and testability requirements. This is a fitness decision, not a fixed code → Jev → LLM cascade. State what is gained, what may be lost, how failure is detected, and what evidence would justify keeping or reversing each substitution.

Preserve a renderer-independent node map. For multi-stage or model-assisted work, define the audit boundary from [workflow observability](references/workflow-observability.md); keep raw evidence and provider payloads in a separately permitted local trace store.

## Use Jev deliberately

Use Jev for narrow typed semantic judgments over supplied state, not open-ended planning, prose generation, tool execution, branching, side effects, or broad retrieval control. Code and tools own rules, source discovery, normalization, deduplication, frontier order, budgets, composition, and confidence gates. Use stronger models only on explicit exception paths whose frequency and value are measured.

Before specifying Jev questions or code, read the available `typesafe-ai` skill completely and follow its routing to current official documentation. If it is unavailable, state that limitation and start from <https://docs.typesafe.ai/llms.txt>. This skill decides *where* Jev fits; current TypeSafe guidance decides *how* to call it.

## Implement within authorization

Preserve the target stack and begin from the approved design handoff. Follow [test-driven workflows](references/test-driven-workflows.md): first observe a meaningful test fail, then implement the smallest slice and keep provider calls mocked by default. Use the target project's interface conventions; for a standalone runner, prefer an importable function plus JSON CLI.

A precise authorization for a live external or paid call in the current task remains valid for that same service, data, cost, target, effect, and scope. Confirm again only when one of those changes materially. General implementation authorization never implies a live call or side effect. Never place credentials, raw identities, or provider payloads in portable logs or returned state.

For durable work, preserve the existing runtime and operational ownership. A new runtime, infrastructure change, deployment, or externally consequential action requires authorization matching that change.

Use [result-envelope.json](assets/templates/result-envelope.json) for bounded results and adapt [async-workflow-snapshot.json](assets/templates/async-workflow-snapshot.json) to an existing durable runtime. These are design templates, not hosted services or universal schemas.

## Keep the product boundary clear

WhatToOffload analyzes, designs, and—when authorized—implements integrations. It is not a scheduler, worker host, persistence layer, deployment system, operations console, or secret manager. Do not claim success from lower cost or latency until the frozen quality boundary passes, and do not create automatic adoption or rollback policy unless the user asks for it.
