# Durable workflow design: `<name>`

## Boundary and ownership

- **Goal:**
- **Trigger:**
- **Terminal outcomes:**
- **Maximum useful duration:**
- **Cancellation behavior:**
- **System of record:**
- **Runtime owner:**
- **Operational owner:**
- **Out of scope:**

## Why this must be durable

Identify the process-lifetime boundary, timer, external event, delayed retry, or human wait that prevents a single bounded invocation from owning the complete flow.

## Workflow view

Render the graph with an available visualization capability. Preserve a renderer-independent description:

```text
request
  -> validate and create run
  -> collect evidence
  -> wait(event: evidence_ready)
  -> judge evidence
     -> uncertain -> wait(review)
     -> accepted -> prepare action
  -> wait(approval)
  -> revalidate prepared action
  -> execute idempotent effect
  -> completed
```

## State transitions

| From | Event or condition | Guard | Activity or transition | To | Timeout / expiry |
| --- | --- | --- | --- | --- | --- |
| | | | | active / waiting / completed / failed / cancelled | |

## Node design

| ID | Purpose | Input → output | Location | Capability role | Concrete implementation | Idempotency | Timeout / retry | Side effect / approval | Skill or docs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | workflow runtime / activity runner / current agent | code / tool / Jev / small LLM / strong LLM or agent / human | | | | | |

## Replacement decisions and balance

Complete one row per material substitution, including retained agent/LLM work when necessary. Apply the same quality boundary to the existing and proposed behavior.

| Existing behavior → proposed executor | Preconditions and evidence available | Expected gain | Capability or coverage at risk | Failure detection → recovery / stop | Comparison that would support or reject it |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

- **Quality boundary and explicitly accepted trade-offs:**
- **Evidence contract, supported scope, and coverage checks:**
- **Missing or unresolved states and next actions:**
- **Recovery budget, preservation of accepted results, and persisted recovery state:**
- **Retained agent supervision and context still required:**

## Exploration contract (when retrieval is broad)

- **Goal, entity identity, and unresolved fields:**
- **Candidate generators and supported search scope:**
- **Candidate representation:** stable ID, source, parent, depth, snippet, provenance, and local context
- **Jev judgment:** primitive, exact decision meaning, question version, and threshold policy
- **Context and batching:** required repeated context, candidates per call, coverage check, and cross-batch composition
- **Persisted frontier:** priority rule, active branches or beam width, visited-source set, duplicate map, and cycle handling
- **Persisted budgets:** maximum depth, pages, Jev calls, elapsed time, tokens, cost, retries, and no-improvement rounds
- **Page-expansion rule:** when a page is worth following and what evidence can stop that branch
- **Stop and handoff:** completed, searched-scope no-match, budget exhaustion, uncertainty, and stronger-model or agent escalation
- **Trace fields, retention, and redaction:**

## Durable state

- **Workflow definition and version:**
- **Workflow ID / run ID source:**
- **Current step and attempt:**
- **State version or concurrency token:**
- **Persisted business references:**
- **Persisted judgment metadata:**
- **Retention and deletion:**
- **Sensitive fields excluded or encrypted:**
- **Schema migration strategy:**

Adapt [async-workflow-snapshot.json](async-workflow-snapshot.json) to the target runtime instead of treating it as a universal schema.

## Events and commands

| Name | Producer | Authentication / authorization | Correlation | Duplicate / late / out-of-order policy | Retained audit data |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## Waits and resumption

| Wait reason | Resume condition | Deadline | Reminder / escalation | Stale-state check |
| --- | --- | --- | --- | --- |
| timer / event / input / review / approval / backoff | | | | |

## Side effects and recovery

| Effect | Idempotency or reconciliation | Unknown-outcome handling | Compensation | Approval owner |
| --- | --- | --- | --- | --- |
| | | | | |

## Runtime fit

- **Existing runtime and evidence of fit:**
- **Required capabilities:** persistence, timers, signals/events, retries, visibility, cancellation, retention
- **Missing capabilities or architecture decision:**
- **Hosting, cost, and operational implications:**

Do not implement a runtime choice that materially changes infrastructure without user authorization.

## Provider capability assumptions

| Capability | Required | verified / unsupported / unknown | Evidence or planned probe |
| --- | --- | --- | --- |
| OpenAI-compatible chat completions | | | |
| Structured JSON output | | | |
| Jev Choice / Noul / Score | | | |
| Provider idempotency | | | |
| Callback or webhook verification | | | |

## Skills used

| Skill | Status | Why it applies | Fallback |
| --- | --- | --- | --- |
| | available / missing / unknown | | |

## Observability

- **Metrics and service-level indicators:**
- **Capture level:** minimal / diagnostic / full_local, and when it changes
- **Portable JSONL audit log, retention, and redaction:**
- **Separate local raw trace store, access, encryption if required, and deletion:**
- **Trace / correlation fields:** run, workflow version, node, subject, source, candidate, batch, decision, evidence, and parent events
- **Candidate coverage and budget events:**
- **Semantic decision, threshold, question/contract version, and reason-code events:**
- **Evidence supplement/replacement and accepted-to-emitted lineage:**
- **Deterministic gap attribution and safe aggregate output:**
- **Portable-log validation and count reconciliation:**
- **Stuck-workflow detection:**
- **Operational review queue:**
- **Runbook owner:**

## Test-first acceptance plan

- First behavior slice and expected failing assertion:
- Test seam, virtual clock, fakes, fixtures, and controlled dependencies:
- Existing behavior that needs characterization tests:
- Old-versus-new comparison on common inputs and acceptance criteria:
- Unsupported-input detection, evidence coverage, and lost-context cases:
- Broad-search batching, cross-batch composition, page-expansion, cycle, exploration-budget, restart, and replay cases:
- Audit lineage, replay idempotency, model-call references, candidate-coverage accounting, terminal reasons, and secret-redaction cases:
- Transition and terminal-state tests:
- Restart and replay tests:
- Duplicate and out-of-order event tests:
- Retry, timeout, and exhaustion tests:
- Idempotency and unknown-outcome tests:
- Approval, expiry, and stale-state tests:
- Cancellation and compensation tests:
- State-schema migration tests:
- Representative Jev / LLM and uncertainty tests:
- Composition-policy and action-suppression tests:
- Provider mocks:
- Focused and broader regression suites:
- Optional live probe requiring confirmation:

## Evaluation and adoption

- **Per-substitution result:** measured benefit, capability loss, and adopt / revise / retain decision
- **Whole-task result:** quality, execution cost, wall time, active processing versus external waits, and supervision
- **Exception effectiveness:** escalation count and denominator, reason, and additional validated outcomes
- **Failure attribution:** discovery / retrieval / parsing / normalization / context packing / judgment / fallback / evidence replacement / handoff / assembly / grading
- **Cost boundary:** recurring execution versus construction, runtime operations, and maintenance
- **Transfer check:** separate development cases from new evaluation inputs; retain initial outcomes

## Implementation plan and authorization boundary

Describe the smallest target-project changes: workflow definition, activities, adapters, state migration, tests, deployment, and observability. Preserve the existing stack and operational ownership.

This document is a design. Do not edit the target project or provision infrastructure until implementation has been explicitly authorized, unless autonomous implementation was already requested. External side effects and live paid API calls retain their own approval stops.
