# Workflow observability and gap attribution

Use this mechanism for a multi-stage workflow with retrieval, semantic decisions, fallback, or quality failures that must be located. A one-step deterministic transform usually needs ordinary application logs instead.

The contract answers where a missing or wrong field first became inevitable. It does not turn WhatToOffload into a trace store, grader, or workflow runtime.

## Normative contract and examples

The formal JSON Schemas are normative for individual records:

- [workflow-audit-event.schema.json](../assets/schemas/workflow-audit-event.schema.json)
- [frozen-field-reference.schema.json](../assets/schemas/frozen-field-reference.schema.json)
- [gap-attribution.schema.json](../assets/schemas/gap-attribution.schema.json)

[workflow-audit-event.json](../assets/templates/workflow-audit-event.json) and [gap-attribution.json](../assets/templates/gap-attribution.json) are examples, not schemas. Cross-event invariants such as declaration order, lineage, terminal coverage, and reconciled counts cannot be expressed fully by an individual-event schema; `scripts/validate_audit_log.py` enforces them with the standard library.

## Keep two linked stores

Write the portable audit log as append-only JSON Lines. It contains pseudonymous IDs, lifecycle events, reason codes, counts, hashes, latency, cost, and safe references. It must not contain raw source text, personal data, credentials, authorization headers, model prompts, provider bodies, URLs that identify a subject, or absolute local paths.

When raw source or exact model payloads are permitted and needed, put them in a separate project-owned local trace store with an explicit retention policy. A portable event may point to a snapshot only through a safe relative or `opaque:` reference plus its SHA-256 content hash. The reference never grants permission to publish the snapshot.

Use one of three capture levels:

- `minimal`: declarations, lineage, decisions, budgets, terminal fields, and summaries;
- `diagnostic`: minimal events plus local snapshots for uncertain, rejected, repaired, or failed paths;
- `full_local`: local snapshots for every semantic and evidence transition during a bounded test, with explicit retention.

The event `privacy` value is one of `metadata`, `pseudonymous`, or `aggregate`; it describes the portable event, not the separate raw trace.

## Vocabulary

Stages follow execution order:

```text
run
discover -> retrieve -> parse -> normalize -> pack -> judge
         -> repair -> accept -> assemble -> grade
```

Only emit transitions that occurred. The allowed event types and their stages are:

| Event type | Allowed stage | Required purpose |
| --- | --- | --- |
| `run_started`, `run_finished` | `run` | Freeze required fields; reconcile final counts |
| `source_declared` | `discover` | Declare a source ID before reference |
| `source_retrieved` | `retrieve` | Record retrieval outcome for a declared source |
| `candidate_declared` | `parse`, `normalize` | Declare a candidate and its source IDs |
| `evidence_declared` | `retrieve`, `parse`, `normalize`, `repair` | Declare evidence linked to candidates and sources |
| `context_packed` | `pack` | Record exact candidate IDs and coverage counts |
| `decision_recorded` | `judge` | Record typed outcome, input candidates, reason, and model trace references when applicable |
| `fallback_started` | `repair` | Record trigger parent and fields the fallback may change |
| `evidence_supplemented`, `evidence_replaced` | `repair` | Record prior/new evidence, candidate and field scope, and declaration parents |
| `field_accepted`, `field_rejected`, `field_quarantined` | `accept` | Record typed handoff or terminal rejection |
| `field_missing` | `accept`, `assemble` | Record a required field with no accepted output |
| `field_emitted` | `assemble` | Record an emitted accepted field |
| `field_graded` | `grade` | Record pass/fail against the frozen reference |
| `budget_recorded` | `discover`, `retrieve`, `pack`, `judge`, `repair` | Record one limit, usage, and exhaustion state |

Every source, candidate, and evidence ID must be declared before use. Accepted and emitted fields must name a declared candidate and declared evidence linked to that candidate. Each field listed by `run_started.required_fields` must have exactly one terminal event: emitted, missing, rejected, or quarantined.

Candidate packing uses `eligible`, `packed`, `excluded`, and `unevaluated`; the final three counts must sum to `eligible`, and `packed` must equal the recorded candidate-ID count. `run_finished.summary` reconciles source, candidate, evidence, decision, budget, and terminal-field event counts.

## Stable reason codes

Use only a code whose boundary changes recovery or analysis:

| Primary boundary | Reason codes |
| --- | --- |
| Discovery | `source_not_discovered` |
| Retrieval | `source_not_retrieved`, `fetch_failed` |
| Parsing | `parser_unsupported` |
| Normalization | `candidate_omitted`, `normalization_loss`, `candidate_overflow` |
| Context packing | `context_omission`, `batch_not_evaluated`, `identity_context_missing` |
| Semantic judgment | `above_threshold`, `below_threshold`, `semantic_rejection`, `ambiguous_candidates`, `provider_failure` |
| Fallback and evidence merge | `exception_not_routed`, `repair_unsupported`, `repair_rejected`, `evidence_overwritten` |
| Handoff and assembly | `typed_handoff_lost`, `assembly_drop`, `output_contract_failure` |
| Grading | `wrong_identity`, `wrong_value`, `missing_evidence`, `reference_or_grader_gap` |
| Trace completeness | `trace_incomplete` |

`budget_exhausted` is attributed to the stage of its `budget_recorded` event because discovery, retrieval, packing, judgment, and repair can have independent budgets.

Store a score and threshold separately from the reason code. Evidence replacement or supplementation must reference the declaration events for both prior and new evidence as explicit parents. A fallback must name its trigger event as a parent and state its field scope.

## Deterministic gap attribution

After execution, join the validated log to a frozen field reference. The reference contains pseudonymous subject/field keys and, when known, expected source, candidate, and evidence IDs; it stores only a value hash when value identity is needed.

For every expected available field that is absent or fails grading, choose the earliest supported boundary:

1. source not discovered;
2. source known but not retrieved;
3. retrieved material not parsed or normalized into the expected candidate;
4. candidate not packed or evaluated;
5. semantic decision rejected it;
6. fallback or evidence replacement removed it;
7. accepted field was lost during handoff or assembly;
8. emitted field failed identity, value, evidence, contract, reference, or grader checks.

Code owns the authoritative result. An LLM may summarize a validated report but must not choose its cause. When IDs, terminal events, or reason-coded lineage are insufficient, emit `primary_stage: trace` and `primary_cause: trace_incomplete` rather than guessing.

Generate a report with:

```bash
python3 scripts/generate_gap_attribution.py audit.jsonl frozen-field-reference.json
```

The JSON output includes reference and workflow versions, causal and contributing events, recommended boundary, replayability, and aggregate cause counts. Replayability means saved events are sufficient to replay the relevant deterministic policy; it does not claim a fresh end-to-end result.

## Validation and controlled improvement

Validate before attributing:

```bash
python3 scripts/validate_audit_log.py audit.jsonl
```

The validator rejects unknown vocabulary, undeclared references, broken accepted-to-emitted lineage, implicit evidence replacement, unscoped fallback, missing required-field terminals, unbalanced coverage or summary counts, unsafe trace references, raw-payload keys, credentials, personal-data-like strings, and absolute paths.

Then freeze workflow, contract, budget, input/case-set, reference, and quality-boundary versions; grade outputs; generate field gaps; aggregate verified causes; change the smallest responsible boundary; and add a regression test. Do not tune a model when discovery omitted the source or add more review when assembly dropped an accepted field.

Publish only explicitly authorized aggregates. Keep task identities, identifying URLs, raw evidence, and provider payloads local even when the repository is private.
