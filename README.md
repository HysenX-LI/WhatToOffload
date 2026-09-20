# WhatToOffload

[简体中文](README.zh-CN.md)

> **Status: Experimental.** The workflow, templates, and evaluation method are still evolving. Validate outputs before relying on them in production.

**Turn repeated agent work into testable software workflows.**

WhatToOffload is an Agent Skill that analyzes an existing task, conversation, SOP, or codebase and identifies work that can move from continuous agent reasoning into deterministic code, existing tools, [Jev](https://docs.typesafe.ai/llms.txt), or LLM services. It also makes explicit what should stay with the agent or a human.

A Skill can make an agent more consistent without making repeated execution cheap: the agent may still need to reread context, choose the next step, call tools, and check results on every run. WhatToOffload looks for the automation boundary where work can run independently of the agent.

[Quick start](#quick-start) · [How it works](#how-it-works) · [Examples](#example-supplier-review) · [Measurements](#measurements) · [Project boundaries](#project-boundaries)

## When to use it

Use WhatToOffload when:

- an agent repeats the same multi-step workflow and spends substantial time or tokens coordinating it;
- a prompt-and-parse step could become a narrow, typed decision;
- deterministic rules, calculations, API calls, or validation are still being performed through agent reasoning;
- a workflow must wait for approvals, callbacks, timers, or retries without keeping an agent in a polling loop;
- you want an evidence-based comparison of scripts, Jev, LLM services, agents, and human review.

It is less useful for a one-off exploratory task whose goal is still changing. It is also not a workflow host: it helps design and integrate a runner, but does not provide scheduling, persistence, deployment, or secret management.

## Quick start

### 1. Install the Skill

In Codex, ask the built-in Skill installer to install the repository root as `what-to-offload`:

```text
Use $skill-installer to install the Skill at the repository root of
https://github.com/HysenX-LI/WhatToOffload and name it what-to-offload.
```

Codex normally detects newly installed Skills automatically; restart it if the Skill does not appear. To inspect the project before installing it, start with [SKILL.md](SKILL.md).

This repository currently ships as a standalone Skill. The installer flow above is intended for local use and evaluation rather than marketplace distribution.

### 2. Analyze a workflow

Give the agent the relevant conversation, task description, codebase, SOP, or execution trace:

```text
Use $what-to-offload to analyze this task.
Identify up to three steps that scripts, Jev, or LLM services could handle,
and which steps should remain with the agent or a human.
For each replacement, explain the benefit, capability loss, failure detection,
and validation method. Propose a plan without editing code.
```

### 3. Design, then implement

After choosing a candidate, ask for a detailed design:

```text
Expand the first proposal. Show the workflow, each step's input and output,
exception handling, handoff conditions, and acceptance tests.
```

When the design is agreed, explicitly authorize implementation:

```text
Implement this design using the project's existing stack.
Validate quality before comparing cost and latency, and document the cases
that still return to the agent or require human review.
```

Live API calls, paid model calls, deployment, and external side effects remain subject to explicit authorization.

## What it produces

WhatToOffload separates analysis, design, and implementation so a recommendation does not silently turn into a code change.

| Mode | Output | Changes code? |
| --- | --- | --- |
| **Analyze** | Up to three leading candidates, prerequisites, benefits, capability loss, risks, and validation plans | No |
| **Design** | Node-by-node workflow, executor choices, contracts, recovery paths, handoffs, and acceptance tests | No |
| **Implement** | Tested runner or project integration using the existing stack | Yes, only when explicitly requested |

Candidates may be **short-lived**—finishing in one invocation—or **durable asynchronous**, where state must survive restarts or wait for an event, timer, retry, review, or approval.

## How it works

For each atomic step, the Skill records both a capability role and a concrete implementation:

| Work in the task | Likely executor | Key question |
| --- | --- | --- |
| Read files, call known APIs, calculate, deduplicate, validate, and save | Deterministic code or an existing tool | Are the rules explicit, and can unsupported inputs be detected? |
| Classify a description or judge whether a candidate meets a condition | Jev | Is the question narrow, typed, and supported by complete candidates and context? |
| Interpret complex material or generate an explanation | LLM service | Is the necessary evidence supplied, can the result be checked, and is there a call budget? |
| Replan around changing goals or negotiate with the user | Current agent or human | Does the work still require open-ended exploration or accountability? |

The result is not a mandatory code → Jev → LLM cascade. Each step goes to the simplest executor that can meet its quality, safety, and testability requirements. Code owns deterministic control flow and side effects; uncertain or unsupported cases follow explicit recovery and handoff paths.

For broad information retrieval, WhatToOffload first lets code and search tools generate a wide set of candidates with provenance, then gives Jev as many relevant options as safely fit while preserving the goal, entity identity, and local evidence. Larger sets are split into self-contained calls and combined through comparable per-item judgments or one final common comparison. Code maintains the exploration frontier, visited sources, and depth, page, call, time, and cost budgets; Jev can also judge whether a page is likely to provide or lead to evidence for an unresolved question. Exhausting a budget leaves the result unresolved rather than turning it into a verified no-match. [Read the Jev-guided bounded exploration method](references/jev-guided-exploration.md).

For multi-stage or model-assisted workflows, WhatToOffload also designs an audit boundary. A portable JSONL log records candidate coverage, semantic decisions, thresholds, reason codes, budgets, evidence lineage, fallback routes, and accepted-to-emitted handoffs. Raw sources and exact model payloads stay in a separate permitted local trace store and are linked by opaque references and hashes. After grading, deterministic gap attribution identifies the earliest causal stage—discovery, retrieval, parsing, normalization, context packing, judgment, fallback, evidence replacement, handoff, assembly, or grading—so the next iteration changes the responsible boundary instead of guessing from the final score. [Read the workflow observability and gap-attribution method](references/workflow-observability.md).

The evaluation method is:

1. Observe the current behavior and its context.
2. Define acceptance before selecting a replacement.
3. Compare executors and the capability each would lose.
4. Specify the evidence and input contract.
5. Bound retries, uncertainty, and handoff behavior.
6. Test old and new behavior on the same cases.
7. Measure the complete task: quality, cost, latency, and remaining agent work.

[Read the full executor-selection method](references/executor-selection.md#work-through-a-replacement).

## Example: supplier review

Suppose an agent reviews supplier quotations every week: it reads files, calculates totals, interprets terms, shortlists offers, and writes an explanation.

| Step | After offloading |
| --- | --- |
| Ingest quotations and revisions | Code parses known formats, checks required material, and detects unsupported inputs |
| Calculate totals and apply explicit constraints | Code performs reproducible calculations and policy checks |
| Judge whether quoted terms satisfy a stated requirement | Jev makes a narrow judgment over the original evidence |
| Resolve exceptional or ambiguous material | An LLM service runs only on an explicit exception branch |
| Change the goal, approve a purchase, or resolve missing evidence | The workflow hands back to the agent or a human |

The design must also say how parser failures, incomplete candidate sets, uncertain judgments, and provider errors are detected. Faster and cheaper execution with missing or unsupported results is not a successful optimization.

See the public examples for [test-failure analysis](examples/code-triage.md), [web research](examples/web-research.md), [candidate screening](examples/business-screening.md), and a [multi-day supplier review](examples/durable-vendor-review.md).

## Measurements

### Long-horizon website task

We compared three execution paths on the same private task. Both Codex paths used Sol high. The WhatToOffload-designed workflow used Jev (`typesafe/jev-1.13`) with DeepSeek-V4.1-Flash on explicit exception paths.

| Path | Execution-model cost | Time | Completion / 100 |
| --- | ---: | ---: | ---: |
| Codex directly | $4.5361 | 13.14 min | 92.8 |
| Codex + task Skill | $3.5562 | 12.72 min | 96.4 |
| WhatToOffload-designed workflow | $0.0472 | 3.40 min | 83.2 |

![Website task comparison](benchmarks/results/website-long-horizon-comparison.svg)

The workflow was cheaper and faster in this run, but it had lower completion than both baselines. There was one run per path, and **none passed strict acceptance**. This is evidence about a specific design tradeoff, not a general success rate. Costs cover model execution only and exclude construction, debugging, and other setup costs. [Read the report and measurement boundaries](benchmarks/results/website-long-horizon.md).

### Synthetic batch task

A second study covers 120 documents, 24 candidates, and three projects, including quotation revisions, conflicting evidence, calculations, rankings, and a report. It compares the same three approaches over three runs per path.

![Three-path batch-task cost and time comparison](benchmarks/results/long-task-comparison.svg)

This measures repeated execution after the program was prepared; one-time construction cost was not fully measured. The task also participated in development, so it is a development case study rather than evidence of unseen-case generalization. [Full results](benchmarks/results/long-task.md) · [Measurement method](benchmarks/README.md)

## Project boundaries

- WhatToOffload is a design and implementation Skill, not a scheduler, worker host, database, queue, deployment platform, operations console, or secret manager.
- Offloading moves necessary reasoning to the appropriate executor; it does not eliminate all model inference.
- Jev cannot select an answer absent from its candidates, scripts can miss unfamiliar formats, and LLM recovery still has cost and failure modes.
- Quality and evidence are acceptance requirements. Cost and latency improvements are evaluated only after result quality.
- External actions and live API calls stay within the user's authorization.

## Repository map

| Path | Contents |
| --- | --- |
| [SKILL.md](SKILL.md) | Agent instructions and operating modes |
| [LICENSE](LICENSE) | MIT license |
| [`references/`](references/) | Executor selection, bounded exploration, workflow observability, workflow classes, safety, uncertainty, and test-driven implementation |
| [`assets/templates/`](assets/templates/) | Candidate analysis, workflow design, audit events, gap attribution, result envelopes, and durable snapshots |
| [`scripts/`](scripts/) | Deterministic helpers, including portable audit-log validation |
| [`examples/`](examples/) | Worked short-lived and durable workflow analyses |
| [`benchmarks/`](benchmarks/) | Benchmark method, fixtures, tests, reports, and published aggregate results |

For Jev implementation details, use the `typesafe-ai` Skill when available and consult the [official TypeSafe documentation](https://docs.typesafe.ai/llms.txt).

## License

WhatToOffload is released under the [MIT License](LICENSE).
