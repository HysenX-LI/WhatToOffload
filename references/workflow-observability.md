# Workflow observability and gap attribution

Use this mechanism when an offloaded workflow has multiple stages, semantic decisions, retrieval, fallback, or a quality metric whose failures need diagnosis. A one-step deterministic transformation usually needs ordinary application logs rather than this audit trail.

The purpose is to answer where a missing or wrong outcome first became inevitable. Final quality metrics cannot distinguish a source that was never retrieved from a correct decision that was later dropped.

## Keep two linked stores

Write an append-only, portable audit log as JSON Lines. It contains stable IDs, lifecycle events, reason codes, counts, hashes, latency, cost, and references. It must be safe to retain with the workflow's other sanitized diagnostics.

Keep raw source snapshots and exact Jev or LLM request and response bodies in a separate local trace store only when they are needed and permitted. The audit log points to those files through opaque references and content hashes. Do not copy raw source text, personal data, credentials, authorization headers, or model prompts into the portable log.

Use three capture levels:

- `minimal`: stage transitions, candidate lineage, decisions, reason codes, budgets, provider usage, and final-field lineage. Enable this for representative production runs.
- `diagnostic`: minimal events plus local request, response, and evidence snapshots for uncertain, rejected, repaired, or failed paths. Prefer this for iterative evaluation.
- `full_local`: local snapshots for every semantic call and evidence transition. Use for bounded test runs with an explicit retention period, not as the default production setting.

The raw trace store and its retention policy belong to the target project. WhatToOffload only specifies the contract.

## Record a candidate and field lifecycle

Use stable `run_id`, `event_id`, `node_id`, `candidate_id`, and hashed or otherwise non-identifying `subject_ref` values. Preserve parent event IDs so a final output can be traced backward.

Useful stages are:

```text
discover -> retrieve -> normalize -> pack -> judge -> extract
         -> repair -> accept/quarantine -> assemble -> grade
```

Record the transitions that actually occur. Do not emit fabricated stages merely to satisfy a diagram. The portable event shape is illustrated in [workflow-audit-event.json](../assets/templates/workflow-audit-event.json).

At minimum, make these facts reconstructable:

- which sources and candidates were generated, deduplicated, excluded, or left unevaluated;
- which candidate IDs and identity context entered every Jev or LLM call;
- the question, contract, parser, normalization, and workflow versions;
- the returned typed decision, score or probability, active threshold, and reason code;
- whether a fetch succeeded and whether its evidence supplemented or replaced earlier evidence;
- why a fallback ran, which fields it could change, and how its output was checked;
- every accepted, rejected, quarantined, missing, and emitted field with candidate and evidence references;
- depth, page, call, time, token, and cost budgets before and after bounded retrieval;
- final quality metrics and provider usage.

Never log only the winning candidate. Candidate coverage and excluded candidates are necessary to distinguish a judgment error from an incomplete input.

## Use stable reason codes

Keep a small project-owned vocabulary. Add a new code only when it changes recovery or analysis. Recommended starting codes are:

| Boundary | Reason codes |
| --- | --- |
| Discovery and retrieval | `source_not_discovered`, `source_not_retrieved`, `fetch_failed`, `budget_exhausted` |
| Parsing and normalization | `parser_unsupported`, `candidate_omitted`, `normalization_loss`, `candidate_overflow` |
| Context packing | `context_omission`, `batch_not_evaluated`, `identity_context_missing` |
| Semantic judgment | `below_threshold`, `semantic_rejection`, `ambiguous_candidates`, `provider_failure` |
| Exception routing | `exception_not_routed`, `repair_unsupported`, `repair_rejected` |
| Handoff and assembly | `evidence_overwritten`, `typed_handoff_lost`, `assembly_drop`, `output_contract_failure` |
| Evaluation | `wrong_identity`, `wrong_value`, `missing_evidence`, `reference_or_grader_gap` |

Store the active threshold and decision score separately from the reason code. Changing a threshold should not require rewriting historical events.

## Attribute each gap deterministically

Join the frozen reference only after execution. For every expected entity or field that is missing, wrong, or unsupported, walk its lineage in this order:

1. If no relevant source was discovered, attribute the gap to discovery.
2. If the source was known but not retrieved, attribute it to retrieval, fetch failure, or budget exhaustion.
3. If the retrieved source contains the value but no candidate represents it, attribute it to parsing or normalization.
4. If a candidate exists but was not packed or evaluated, attribute it to context packing or budget policy.
5. If it was evaluated and rejected, attribute it to the semantic decision or threshold; retain the exact decision event.
6. If it was selected but fallback or verification removed it, attribute it to exception validation or evidence replacement.
7. If it was accepted but not emitted, attribute it to handoff or assembly.
8. If it was emitted but grading rejects it, attribute it to identity, value, evidence, output contract, or the reference/grader.

Assign the earliest causal boundary as `primary_cause`. Preserve later contributing events separately. The gap-report shape is illustrated in [gap-attribution.json](../assets/templates/gap-attribution.json).

Do not let an LLM assign the authoritative cause from a prose trace. Code should derive the stage from lifecycle events. An LLM may summarize a validated gap report or group unfamiliar examples for review.

## Turn diagnosis into a controlled improvement loop

1. Freeze the workflow version, question and contract versions, budgets, reference, and acceptance criteria.
2. Run representative cases with minimal or diagnostic capture.
3. Validate the audit log before interpreting quality. Use `scripts/validate_audit_log.py` when adopting this repository's event contract.
4. Grade the final result, then generate field-level gap attribution.
5. Aggregate primary causes, recovery success, cost, and latency by stage and reason code.
6. Change the smallest boundary that addresses the dominant verified cause: candidate generator, parser, context packer, question, threshold, fallback, evidence merge, or assembler.
7. Replay deterministic policy changes against saved events where possible. Treat threshold replay as a counterfactual, not as a fresh end-to-end result.
8. Add a contract or characterization test for the demonstrated failure.
9. Rerun the inspected case as a post-inspection regression test and use a separately frozen case for the next transfer claim.

Do not tune a Jev prompt when the correct candidate was absent, or add more LLM review when assembly dropped an already accepted value. The audit boundary should make such category mistakes visible.

## Gate adoption on trace completeness

Before using the log to justify a workflow change, require:

- every emitted field has an earlier accepted candidate and at least one evidence reference;
- every unresolved required field has a terminal reason code;
- every semantic call records the candidate IDs it received plus request, response, model, and contract references;
- candidate packing records eligible, packed, and excluded counts;
- accepted evidence is never silently replaced; replacement has an explicit event and parent lineage;
- the run-finished summary agrees with emitted and missing event counts;
- the portable log passes secret and raw-payload checks.

An incomplete trace can still reveal a problem, but it cannot establish that another stage was correct.

## Publish only safe aggregates

Keep task identities, source URLs when identifying, raw evidence, and provider payloads local unless release is explicitly authorized. Reusable reports should contain counts, rates, reason-code distributions, quality, latency, cost, workflow hashes, and stated limitations. A private repository does not by itself change the data-release boundary chosen for the task.
