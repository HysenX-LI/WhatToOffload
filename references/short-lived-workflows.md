# Short-lived workflow analysis

Use this playbook to turn an existing conversation, project, SOP, or workflow into a small set of defensible offload candidates.

## Phase 1 boundary

A short-lived bounded subflow:

- starts from an explicit input contract;
- completes in one invocation or returns a caller-managed handoff;
- has a defined success result and finite failure paths;
- can receive all required context explicitly;
- does not depend on this skill to host, schedule, persist, or deploy it.

Do not reinterpret a long-running or event-driven workflow as short-lived merely to fit Phase 1. Keep durable timers, queues, cross-day waits, background workers, and stored orchestration out of the design.

## Evidence gate

Inspect available sources before asking questions:

- current and referenced conversation history;
- repository entry points, tests, prompts, schemas, configuration, and logs;
- SOPs, diagrams, forms, policies, and representative records;
- available tools, APIs, skills, and permission boundaries.

Before recommending candidates, establish at least:

- the workflow goal and trigger;
- inputs actually available at decision time;
- expected outputs and downstream consumers;
- current steps, including repeated agent supervision;
- side effects and who is accountable for them;
- important failure costs and known edge cases.

Ask only for missing facts that can change the boundary, executor, safety policy, or ranking. If such a fact is missing, return questions rather than a speculative recommendation.

## Decompose at two levels

### Atomic node

An atomic node has one coherent responsibility that can be tested separately. Examples include parsing a log, fetching a page, selecting a category, rating evidence relevance, drafting a summary, or approving an external action.

Atomic does not mean “one line of code.” A node can contain a small deterministic procedure as long as it has one observable contract.

### Bounded subflow

Combine adjacent nodes when they:

- share an input and outcome;
- form a reusable unit;
- can expose a clean boundary to the caller;
- avoid excessive serialization or model round trips;
- have a coherent failure and review policy.

Recommend bounded subflows as the primary offload units. Preserve their atomic-node breakdown so the user can understand and change executor choices.

## Candidate eligibility

A strong candidate usually has several of these properties:

- repeated or high-volume execution;
- substantial current-agent context or supervision;
- structured inputs and outputs;
- explicit context can replace hidden conversational context;
- deterministic or bounded semantic steps dominate;
- representative cases and acceptance rules are available;
- failures can be detected and contained;
- side effects can be separated behind approval;
- the result is reusable by more than one caller.

Keep a node or subflow in the current agent when it depends on ongoing goal negotiation, broad exploration, tacit context that cannot yet be made explicit, frequent user judgment, unavailable tools, or exceptions that dominate the normal path.

## Compare candidates without fake precision

Evaluate each candidate qualitatively on:

| Dimension | Question |
| --- | --- |
| Boundary clarity | Are input, output, completion, and failure explicit? |
| Agent supervision removed | How much repeated context and monitoring leaves the current conversation? |
| Replaceability | How much work belongs to deterministic code, tools, or bounded judgments? |
| Reuse and frequency | Will the unit run often or serve multiple callers? |
| Verifiability | Can contracts, examples, and invariants detect regressions? |
| Cost and latency | Will the new composition improve or worsen practical execution? |
| Implementation effort | How much adapter, runner, and integration work is required? |
| Uncertainty | Are ambiguous cases rare, detectable, and recoverable? |
| Side-effect risk | Are consequential actions isolated behind approval? |

Use `high`, `medium`, `low`, or a short explanation per dimension. Do not sum the labels into a decimal score. Recommend an order and explain the trade-off.

## Progressive output

The first analysis should contain:

1. an evidence summary and any resolved assumptions;
2. no more than three leading candidate cards;
3. a retained-nodes table with reasons;
4. what can be expanded into a detailed node map or subflow map;
5. a request for the user to select a candidate, unless autonomous selection was explicitly authorized.

Do not generate implementation files during this phase.

