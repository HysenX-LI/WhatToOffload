# Durable asynchronous workflow design

Use this playbook when a candidate must survive process restarts or wait for timers, callbacks, external events, delayed retries, human input, review, or approval. The goal is a reviewable design for a target runtime, not a new universal workflow engine.

## Qualify the candidate

A workflow is durable when correctness depends on remembering progress beyond one process lifetime. Common signals include:

- work continues across minutes, hours, or days because an external party must respond;
- a timer, scheduled retry, webhook, queue message, or callback resumes progress;
- a worker may restart after acknowledging work;
- multiple deliveries, late events, or out-of-order events are normal;
- a human approval or review must survive the current conversation;
- a side effect must be reconciled after a timeout or partial failure.

Elapsed time alone is not enough. A long computation can be one bounded job. A short approval wait can be durable. If the agent only needs to invoke one external job and later read its terminal result, prefer a thin job adapter over redesigning the external system as a workflow.

## Evidence gate

Before recommending or designing a durable candidate, establish:

- trigger, terminal outcomes, maximum useful duration, and cancellation expectations;
- event producers, delivery mechanism, authentication, correlation fields, and delivery guarantees;
- the system of record for workflow state and the owner responsible for operating it;
- retention, privacy, tenant-isolation, and deletion requirements;
- side effects, approval authority, and whether each effect supports idempotency or reconciliation;
- timeout, retry, service-level, observability, replay, and backfill expectations;
- the target project's existing workflow engine, queue, database, deployment, and monitoring stack.

Ask for missing facts that materially change runtime choice, state ownership, safety, or recovery. Do not fill infrastructure gaps by assumption.

## Separate orchestration from activities

The durable runtime owns state transitions, timers, event correlation, retry scheduling, and recovery. Activities perform bounded work such as an API call, deterministic transformation, Jev judgment, LLM generation, or external side effect.

Design each activity with an explicit input and result contract. Use the ordinary five-state result envelope for activity outcomes when it fits. The durable workflow then translates those outcomes into lifecycle transitions:

- `completed` may advance to the next node or finish the workflow;
- `needs_input`, `needs_review`, or `needs_approval` normally move the workflow to `waiting` with a specific wait reason;
- retryable `failed` schedules a bounded retry;
- terminal `failed` ends the workflow or enters an explicit recovery path.

Do not keep a worker alive while waiting. Persist the transition and resume from a durable signal, timer, or event.

## Model lifecycle and waiting separately

Use a small lifecycle vocabulary unless the target runtime already has one:

| Lifecycle | Meaning |
| --- | --- |
| `active` | A runnable step exists or work is executing. |
| `waiting` | No work should run until a recorded condition is satisfied. |
| `completed` | The intended terminal result is committed. |
| `failed` | The workflow reached an unrecoverable terminal failure. |
| `cancelled` | An authorized cancellation ended further work. |

For `waiting`, record one reason such as `timer`, `event`, `input`, `review`, `approval`, or `backoff`, plus the condition needed to resume. Keep lifecycle and wait reason separate so monitoring and business logic do not parse free text.

The example in [../assets/templates/async-workflow-snapshot.json](../assets/templates/async-workflow-snapshot.json) is a portable design aid, not a mandatory storage schema. Prefer the target runtime's native representation when it provides equivalent semantics.

## Give every transition stable identity

Record identities sufficient for deduplication and diagnosis. Typical fields are:

- workflow definition and version;
- workflow ID and run ID;
- current step ID and attempt;
- event or command ID and correlation ID;
- state version or compare-and-swap token;
- idempotency key for repeatable external effects.

Use opaque identifiers that reveal no secret or personal data. Define which component creates each identifier and how long deduplication records live. A retry must reuse the logical operation's idempotency key; a new user-requested action must get a new one.

## Treat events as untrusted input

For every resuming event, specify:

- authentication and authorization checks;
- schema version and validation;
- correlation to one workflow and expected step;
- duplicate, late, missing, and out-of-order handling;
- event time versus receipt time;
- whether accepting the event causes a side effect;
- what safe data is retained for audit.

Reject or quarantine an event that cannot be correlated safely. Do not advance merely because an event has a familiar shape.

## Design retries, timeouts, and recovery

Retry only failures that are transient and safe to repeat. Bound retries by attempts and elapsed time, use backoff with jitter, and honor provider guidance. Keep the activity timeout shorter than the business deadline.

For each side effect, choose one of:

- provider-supported idempotency;
- an application outbox or equivalent atomic handoff;
- read-after-timeout reconciliation before retry;
- an explicit human recovery path when the outcome cannot be determined.

Compensation is a new, authorized business action, not a magical rollback. Define its preconditions, side effects, failure policy, and accountable owner. Do not compensate automatically when the reverse action is risky or semantically different.

After retry exhaustion, route to a visible terminal failure or operational review queue. Never leave a workflow silently stuck.

## Keep semantic nodes stateless and reproducible

Jev and LLM activities receive a versioned snapshot of the facts needed for that invocation. They do not own durable memory or decide the next workflow transition.

Persist enough metadata to explain or reproduce the decision without storing unnecessary sensitive content:

- input record references and versions;
- question, prompt, or policy version;
- provider and model identifier returned by the service when available;
- structured answer, probability or confidence fields that affect routing;
- timestamp and safe usage diagnostics.

On resume, detect whether source facts or policy versions changed. Reuse a prior judgment only when its inputs and meaning are still valid; otherwise re-evaluate. Jev questions over one state are independent, so later-stage questions that require new evidence belong in a new activity.

Before specifying a Jev activity, read the current `typesafe-ai` skill and its routed official documentation. Keep control flow, retries, permissions, and side effects in code or the workflow runtime.

## Make human waits durable

An approval or review request should identify the workflow, step, prepared action, relevant evidence, expiry, and permitted responders. The resume action must be authenticated, authorized, one-time or idempotent, and correlated to the state version that produced it.

Before performing an approved side effect, verify that the approval is unexpired and the prepared action still matches current state. If material state changed, invalidate the approval and request a new one.

Define reminders and escalation separately from approval. Silence is not approval.

## Select a runtime deliberately

Prefer an existing runtime already operated by the target project. Verify that it can provide the required persistence, timers, event delivery, idempotency support, visibility, cancellation, and retention.

If none exists, present a small set of architecture categories and the evidence needed to choose among them, such as a managed durable orchestrator, an existing job queue plus application state, or a database-backed state machine. Runtime selection changes infrastructure, cost, and operational responsibility, so obtain the user's decision or explicit authorization before implementing it.

Do not generate an ad hoc scheduler or infinite polling loop as a fallback. Do not claim exactly-once execution; design for at-least-once delivery and idempotent effects unless the chosen system provides stronger guarantees that have been verified.

## Validate the design

Test observable transitions and recovery behavior:

- happy-path completion and terminal result;
- worker restart at every checkpoint;
- duplicate, delayed, missing, and out-of-order events;
- stale state version and concurrent resume attempts;
- retryable failure, retry exhaustion, and backoff timing;
- side-effect timeout with unknown outcome and reconciliation;
- approval expiry, rejection, duplicate approval, and state change after approval;
- cancellation before, during, and after an activity;
- workflow-definition and persisted-state version migration;
- redaction of secrets and unnecessary source data from state, logs, and traces;
- representative Jev or LLM cases, including uncertainty and provider failure.

Use mocks and deterministic clocks by default. A real external API probe still requires explicit confirmation immediately before the call.
