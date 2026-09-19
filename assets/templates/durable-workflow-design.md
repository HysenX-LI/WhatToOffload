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
- **Structured logs and redaction:**
- **Trace / correlation fields:**
- **Stuck-workflow detection:**
- **Operational review queue:**
- **Runbook owner:**

## Test-first acceptance plan

- First behavior slice and expected failing assertion:
- Test seam, virtual clock, fakes, fixtures, and controlled dependencies:
- Existing behavior that needs characterization tests:
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

## Implementation plan and authorization boundary

Describe the smallest target-project changes: workflow definition, activities, adapters, state migration, tests, deployment, and observability. Preserve the existing stack and operational ownership.

This document is a design. Do not edit the target project or provision infrastructure until implementation has been explicitly authorized, unless autonomous implementation was already requested. External side effects and live paid API calls retain their own approval stops.
