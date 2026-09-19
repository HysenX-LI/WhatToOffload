# Example: durable vendor review

This example offloads a multi-day vendor review that waits for documents, evaluates evidence, requests human review when uncertain, and requires approval before changing the vendor record.

## Before

An agent repeatedly checks whether a vendor uploaded documents, remembers which checks passed, follows up after deadlines, re-reads policy, asks a reviewer about ambiguous evidence, and finally updates the procurement system after approval. The conversation itself is acting as memory and scheduler.

## Why it is durable

- documents may arrive through callbacks over several days;
- reminders and the submission deadline must survive process restarts;
- uploads can be duplicated or arrive out of order;
- semantic uncertainty can create a human-review wait;
- final approval may arrive after the original agent session ends;
- the procurement update is a side effect with an unknown-outcome risk.

## Proposed boundary

```text
review request
  -> validate and create durable run
  -> request required documents
  -> wait(event: document_uploaded | timer: reminder/deadline)
  -> validate and normalize evidence
  -> judge relevance, policy support, and risk
     -> uncertain -> wait(review)
     -> insufficient -> wait(input)
     -> acceptable -> draft recommendation
  -> wait(approval)
  -> revalidate approval and state version
  -> update vendor record idempotently
  -> completed | failed | cancelled
```

## Input and terminal result

Start command:

```json
{
  "command_id": "cmd_example_001",
  "vendor_id": "vendor_example_789",
  "policy_version": "2026-09",
  "required_document_types": [
    "security_questionnaire",
    "data_processing_terms"
  ],
  "submission_deadline": "2030-01-22T10:00:00Z"
}
```

Successful terminal result:

```json
{
  "workflow_id": "wf_example_123",
  "lifecycle": "completed",
  "result": {
    "decision": "approved",
    "vendor_record_id": "vendor_example_789",
    "evidence_versions": ["evidence_4", "evidence_7"]
  }
}
```

The payload stores references and versions rather than copying full sensitive documents into workflow state.

## Node map

| Node | Location | Capability role | Concrete implementation | Durable concern |
| --- | --- | --- | --- | --- |
| Create review run | Workflow runtime | Deterministic code | Existing project orchestrator | Deduplicate `command_id`; persist workflow version |
| Request and receive documents | Runtime + existing API | Tool / API | Procurement portal and authenticated callback | Correlate events; handle duplicates and deadline |
| Validate documents | Activity runner | Deterministic code | Schema, file-type, malware, and required-field checks | Safe bounded retry; retain source references |
| Judge document relevance | Activity runner | Jev | Noul per required evidence condition | Persist question version and probability used by policy |
| Score policy risk | Activity runner | Jev | Score with concrete risk levels | Route uncertain output to review; code owns thresholds |
| Draft recommendation | Activity runner | Smaller LLM | Configurable OpenAI-compatible endpoint | Generated prose only; evidence IDs constrain claims |
| Resolve ambiguity | Human wait | Human | Existing review inbox | Authenticated, expiring, state-version-bound response |
| Approve vendor change | Human wait | Human | Existing approval system | Silence is not approval; approval can expire |
| Update vendor record | Activity runner | Existing API | Procurement API | Idempotency key and read-after-timeout reconciliation |
| Change goals or policy | Current agent | Agent/user judgment | Host conversation | Requires open-ended negotiation and new workflow version |

## Illustrative orchestration shape

Adapt this shape to the target runtime rather than implementing the loop directly:

```python
async def vendor_review_workflow(start, runtime, activities):
    state = await runtime.create_or_load(start, dedupe_key=start["command_id"])

    while not state.has_all_required_documents():
        event = await runtime.wait_for_event_or_timer(
            event="document_uploaded",
            deadline=state.submission_deadline,
            reminders=state.reminder_schedule,
        )
        state = apply_validated_event(state, event)

    evidence = await activities.validate_documents(state.document_refs)
    judgment = await activities.judge_evidence(
        evidence_refs=evidence.refs,
        policy_version=state.policy_version,
    )

    if judgment.status == "needs_review":
        review = await runtime.wait_for_authorized_review(
            prepared_from_state_version=state.version,
            expires_at=state.review_deadline,
        )
        state = apply_review(state, review)
    elif judgment.status == "needs_input":
        return await runtime.wait_for_input(judgment.required_action)
    elif judgment.status == "failed":
        return await runtime.fail(judgment.diagnostics)

    recommendation = await activities.draft_recommendation(state.safe_evidence_refs)
    approval = await runtime.wait_for_authorized_approval(
        prepared_action=recommendation.prepared_action,
        prepared_from_state_version=state.version,
    )
    await runtime.assert_current(approval.prepared_from_state_version)

    record = await activities.update_vendor(
        recommendation.payload,
        idempotency_key=state.vendor_update_key,
    )
    return await runtime.complete({"decision": "approved", "record_id": record.id})
```

The apparent loop is workflow-definition pseudocode. A durable runtime must suspend it without holding a process open and resume it from persisted state.

## Jev activity boundary

At each judgment, provide a current, versioned state containing only the relevant extracted text, document type, and policy criteria. Do not ask Jev to remember earlier uploads, wait for later documents, send reminders, choose retry timing, or approve the vendor.

Independent questions over the same evidence can be batched. A later question that requires a reviewer response or new document belongs to a new request after the workflow resumes.

## Recovery policies

- Duplicate upload events reuse the event ID and do not create duplicate evidence records.
- An event for an expired or completed run is retained as a safe audit reference but does not resume work.
- A retryable model or document-service failure uses bounded backoff; exhaustion creates an operational review item.
- A timeout while updating the vendor record triggers a read-after-timeout check before any retry.
- Approval is invalidated if evidence, policy version, recommendation payload, or workflow state version changes.
- Cancellation stops future activities but does not pretend already completed external effects were rolled back.

## Representative tests

- The workflow completes when all required documents arrive once and the final approval is valid.
- Duplicate and out-of-order uploads do not duplicate evidence or skip required checks.
- A missing document deadline produces a visible terminal or review outcome according to policy.
- Low-confidence or conflicting judgments wait for review with compact evidence.
- Worker restart at every wait and activity boundary produces the same logical result.
- Two concurrent approval events allow only one state transition.
- An expired or stale approval cannot trigger the vendor update.
- Unknown outcome from the vendor update reconciles before retry.
- State snapshots, logs, and diagnostics contain no credentials or raw document bodies.
