# Short-lived workflow design: `<name>`

## Boundary

- **Goal:**
- **Trigger:**
- **Input contract:**
- **Successful output:**
- **Termination:**
- **Out of scope:**

## Workflow view

Render the connection graph with an available visualization capability. Preserve a compact renderer-independent description here:

```text
input
  -> validate
  -> gather
  -> judge
     -> accepted -> produce result
     -> uncertain -> needs_review
  -> side effect ready -> needs_approval
```

## Node design

| ID | Purpose | Input → output | Location | Capability role | Concrete implementation | Acceptance / uncertainty | Failure / retry | Side effect / approval | Skill or docs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | | | current agent / runner | code / tool / Jev / small LLM / strong LLM or agent / human | | | | | |

## Replacement decisions and balance

Complete one row per material substitution. Include a retained agent/LLM node when removing it would lose necessary capability. Benefits remain hypotheses until measured.

| Existing behavior → proposed executor | Preconditions and evidence available | Expected gain | Capability or coverage at risk | Failure detection → recovery / stop | Comparison that would support or reject it |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

- **Quality boundary and explicitly accepted trade-offs:**
- **Evidence contract:** candidate values, source/context/ownership where relevant, supported scope, and coverage checks
- **Missing or unresolved states and next actions:** distinguish unsearched evidence, retrieval failure, scoped no-match, and ambiguity when their recovery differs
- **Recovery budget and preservation of accepted results:**
- **Retained agent supervision and context still required:**

## Retrieval contract (when retrieval is broad)

- **Goal, entity identity, and unresolved fields:**
- **Candidate generators and supported search scope:**
- **Candidate representation:** stable ID, source, parent, depth, snippet, provenance, and local context
- **Source-role and format policy:** primary and identity-owned sources, aggregators, supported parsers, and unsupported-input detection
- **Deterministic frontier policy:** priority rule, visited-source and cycle handling, and explicit expansion rules
- **Narrow semantic exceptions:** exact decision, supplied evidence, executor, threshold, and why code cannot decide it
- **Budgets:** maximum depth, pages, elapsed time, tokens, cost, retries, and no-improvement rounds; include semantic-call limits when used
- **Evidence merge rule:** when new evidence supplements, conflicts with, or explicitly replaces earlier evidence
- **Stop and handoff:** completed, searched-scope no-match, budget exhaustion, uncertainty, and stronger-model or agent escalation
- **Trace fields and redaction:**

## Runner contract

- **Importable entry point:**
- **JSON CLI invocation:**
- **Configuration variables:** names only; never values
- **Caller-managed resume fields:**
- **Result-envelope statuses used:**

## Audit and gap attribution (when the workflow is multi-stage or model-assisted)

- **Capture level:** minimal / diagnostic / full_local, and when it changes
- **Portable audit path and retention:** JSONL metadata, IDs, reason codes, usage, and hashes
- **Local trace path and retention:** raw evidence and provider request/response snapshots; state who may access it
- **Stable IDs and lineage:** run, node, subject, source, candidate, batch, decision, evidence, and parent events
- **Candidate coverage events:** eligible, packed, excluded, unevaluated, and budget-exhausted counts
- **Decision events:** executor, model, contract/question version, input candidates, output, score, threshold, and reason
- **Evidence merge policy:** supplement versus explicit replacement; failed fetches cannot silently erase discovery evidence
- **Terminal field events:** accepted, rejected, quarantined, missing, and emitted
- **Gap attribution output:** frozen reference version, earliest causal stage, reason code, contributing events, and replayability
- **Portable-log validation:** trace completeness, count reconciliation, and secret/raw-payload checks
- **Safe aggregate output:** non-identifying quality, reason-code distribution, calls, latency, cost, and limitations

## Provider capability assumptions

| Capability | required | verified / unsupported / unknown | Evidence or planned probe |
| --- | --- | --- | --- |
| OpenAI-compatible chat completions | | | |
| Structured JSON output | | | |
| Tool calling | | | |
| Jev Choice / Noul / Score | | | |
| Probabilities and confidence | | | |

## Skills used

| Skill | Status | Why it applies | Fallback |
| --- | --- | --- | --- |
| | available / missing / unknown | | |

## Implementation plan

Describe the smallest changes needed in the target project. Preserve its language, package manager, test stack, and existing authorization boundaries.

## Test-first acceptance plan

- First behavior slice and expected failing assertion:
- Test seam, fakes, fixtures, and controlled dependencies:
- Existing behavior that needs characterization tests:
- Old-versus-new comparison on common inputs and acceptance criteria:
- Unsupported-input detection, evidence coverage, and lost-context cases:
- Broad-retrieval source ordering, supported formats, normalization, page expansion, cycles, evidence merge, and budget cases:
- Audit lineage, model-call references, candidate-coverage accounting, terminal reasons, and secret-redaction cases:
- Contract tests:
- Representative semantic cases:
- Composition-policy and uncertainty-routing tests:
- Uncertainty and review cases:
- Side-effect approval cases:
- Idempotency and unknown-outcome cases:
- Provider mocks:
- Focused and broader regression suites:
- Optional live probe requiring confirmation:

## Evaluation and adoption

- **Per-substitution result:** measured benefit, capability loss, and adopt / revise / retain decision
- **Whole-task result:** quality, model cost, wall time, retrieval/retries, and remaining supervision
- **Exception effectiveness:** escalation count and denominator, reason, and additional validated outcomes
- **Failure attribution:** discovery / retrieval / parsing / normalization / context packing / judgment / fallback / evidence replacement / handoff / assembly / grading
- **Cost boundary:** recurring execution versus construction and maintenance; unmeasured costs remain unknown
- **Transfer check:** separate development cases from new evaluation inputs; retain initial outcomes

## User authorization boundary

State explicitly that this document is a design. Do not edit the target project until implementation has been authorized, unless autonomous implementation was already requested.
