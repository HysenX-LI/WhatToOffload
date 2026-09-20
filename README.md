# WhatToOffload

[中文说明](README.zh-CN.md)

**Turning a task into a Skill can still leave repeated execution consuming substantial agent reasoning resources.**

A Skill gives an agent instructions and reusable knowledge. As long as the agent advances the workflow step by step, it must keep reading context, deciding what comes next, calling tools, and checking results. Even when a Skill includes helper scripts, the remaining coordination and judgments can consume substantial tokens and time.

**WhatToOffload aims to move more of that work into scripts, Jev, and LLM services, reducing the need for continuous agent reasoning and coordination across repeated runs.**

This project is itself a Skill. It guides an agent to inspect an existing task, identify steps worth replacing, design the division of work, and implement and test it when authorized. The resulting program handles routine execution; work that still needs open-ended exploration, negotiation with the user, or recovery beyond its capabilities returns to the agent.

## How further offloading works

“Offloading” means turning work that the agent would otherwise advance on every run into steps a program can execute directly.

| Work within a task | Possible executor | What must be checked |
| --- | --- | --- |
| Read files, call existing APIs, calculate, deduplicate, validate, and save results | Scripts and existing tools | Are the rules explicit, and can unsupported inputs be detected? |
| Classify a description or judge whether a candidate meets a condition | Jev | Is the question narrow enough, with adequate candidates and context? |
| Interpret complex material, generate explanations, or handle cases needing additional reasoning | LLM service | Is the necessary evidence supplied, can the output be verified, and is there a call budget? |
| Respond to changing goals, replan, or negotiate with the user | Agent or human | Does the work still require open-ended exploration and conversation? |

Jev is a TypeSafe model for narrow judgments whose outputs code can use directly, such as choosing a candidate or judging whether a condition holds. LLM services handle generation or more complex reasoning through an API. Code connects the steps, passes evidence, manages retries, and saves results.

**Offloading places necessary reasoning where it fits. It does not eliminate all model inference.** A task need not use all three execution methods, and a Jev judgment does not automatically need an LLM review.

## An example

Suppose you ask an agent to process supplier quotations every week: read files, calculate amounts, interpret terms, shortlist offers, and write an explanation.

WhatToOffload can help divide that work into:

1. **Scripts** read the files, check for missing material, and calculate amounts under explicit rules.
2. **Jev** judges whether quoted terms satisfy predefined requirements using the source text.
3. **An LLM service** handles material the scripts and Jev cannot reliably resolve, and drafts an explanation from verified results.
4. **Code** assembles the results and unresolved questions, handing back to the agent when material is missing or the goal must change.

Each replacement has a cost: scripts can miss unfamiliar formats, Jev cannot select an answer absent from its candidates, and LLM recovery still incurs spend. The design must explain how these failures are detected, when to gather more evidence, and when to stop and hand back.

## How to use it and what you receive

Provide an existing conversation, task description, codebase, or execution trace to an agent that can read this Skill. The entry point is [SKILL.md](SKILL.md). Start with a request such as:

```text
Use $what-to-offload to analyze this task.
Identify specific steps that scripts, Jev, or LLM services could handle,
and which should remain with the agent. Explain each replacement's benefit,
capability loss, and validation method. Propose a plan without editing code.
```

The agent inspects the available material and normally recommends up to three candidates. Each recommendation describes the current agent behavior, proposed executor, prerequisites, benefits, risks, and a way to test the substitution.

After choosing a candidate, ask for a design:

```text
Expand the first proposal: show how the steps connect, the input and output
of each step, exception handling, and the tests needed to validate it.
```

Once the design is agreed, request implementation:

```text
Implement this design using the project's existing stack.
Validate result quality before comparing cost and latency, and explain
which situations still require the agent.
```

The implementation may be functions in an existing project, a directly callable execution program (runner), or steps integrated into an existing workflow system. Live API calls and external actions must remain within the user's authorization.

## How to decide whether a replacement is worthwhile

WhatToOffload uses seven steps to look beyond call counts and prices:

1. **Observe the current behavior:** what exactly is being replaced, and what context does it depend on?
2. **Define acceptance:** which results must be correct, complete, and supported by evidence?
3. **Compare executors:** what can scripts, Jev, and LLMs do, and what capability might each replacement lose?
4. **Specify evidence:** are candidates complete enough, and are sources and context preserved?
5. **Design recovery:** handle insufficient evidence, parser failures, and uncertain judgments according to their cause.
6. **Test the substitution:** compare old and new behavior on the same inputs and requirements.
7. **Evaluate the complete task:** measure quality, cost, latency, and remaining agent work together.

**Lower cost and latency with more missing results do not establish a successful optimization.** Building and maintaining a program also costs effort; a good choice for repeated execution may not suit a one-time task. [Read the full method](references/executor-selection.md#work-through-a-replacement).

## Measurement: a long-horizon website task

We compared three execution paths on the same private task. Both Codex paths use Sol high. The WhatToOffload path uses Jev (`typesafe/jev-1.13`) and DeepSeek-V4.1-Flash (`deepseek-flash` API alias), with DeepSeek handling explicit exceptions.

| Path | Execution-model cost | Time | Completion / 100 |
| --- | ---: | ---: | ---: |
| Codex directly | $4.5361 | 13.14 min | 92.8 |
| Codex + task Skill | $3.5562 | 12.72 min | 96.4 |
| WhatToOffload-designed workflow | $0.0472 | 3.40 min | 83.2 |

![Website task comparison](benchmarks/results/website-long-horizon-comparison.svg)

In this execution, the workflow cost less and finished sooner, but its completion score was below both baselines. One run per path is reported, and **none passed strict acceptance**; these results do not establish a general success rate. Completion measures information coverage, while strict acceptance also checks precision, evidence, and complete deliverables.

Costs cover model execution only. Codex spend is an API-equivalent estimate from actual session tokens; construction, debugging, and other excluded costs are outside the table. Task details and raw material remain local; only anonymized aggregate results are published. [Full report and measurement boundaries](benchmarks/results/website-long-horizon.md).

## Another measurement: a synthetic batch task

This task covers 120 documents, 24 candidates, and three projects, including quotation revisions, conflicting evidence, calculations, rankings, and a report. It compares the same three approaches, with three runs per path.

![Three-path batch-task cost and time comparison](benchmarks/results/long-task-comparison.svg)

These measurements cover repeated execution after the program is prepared; one-time construction cost was not fully measured. The task was used in development, so this is a development case study rather than a guarantee for new tasks or production. [Full results](benchmarks/results/long-task.md) · [Measurement method](benchmarks/README.md).

## Further reading

- **Public examples:** [test-failure analysis](examples/code-triage.md), [web research](examples/web-research.md), [candidate screening](examples/business-screening.md), and [multi-day supplier review](examples/durable-vendor-review.md).
- **Methods and templates:** [executor selection](references/executor-selection.md), [testing and acceptance](references/test-driven-workflows.md), and [workflow design template](assets/templates/workflow-design.md).
- **Tasks that wait or resume:** for multi-day work, approval waits, or execution that must survive a restart, see [durable workflow design](references/durable-async-workflows.md).
- **Jev implementation:** use the available `typesafe-ai` Skill and [official TypeSafe documentation](https://docs.typesafe.ai/llms.txt) for API and usage guidance.

This repository provides Skill instructions, references, templates, examples, and measurement reports. The Skill is not installed automatically; generated workflows run in your project environment. Where scheduling, persisted state, or deployment is needed, it helps select and integrate the relevant systems rather than hosting the workflow itself.
