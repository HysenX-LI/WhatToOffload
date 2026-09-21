# Public supplier-screening experiment v1

This protocol is written before implementation. Historical results are immutable.
This is one bounded synthetic workflow, not a procurement or workflow platform.

## Acceptance contract

Input is a request, explicit policy and vendor records with individually identified
profile, independent reference, region confirmation and quotation revisions.
No contact, purchase, rejection message or other external action is executed.

1. Select the highest quotation revision. Identical duplicate source IDs collapse;
   conflicting content with the same source ID or revision requires review.
2. Missing profile, regions, quote, amount or currency requires input. A reference
   is required only when the policy says so. Never inherit a superseded currency.
3. A wrong currency, excess price or missing required region makes a complete
   record ineligible. Budget equality passes. Prices use decimal arithmetic.
4. When an independent reference is required, classify its relation to the
   profile for the requested domain: corroborated, unrelated, conflict, unclear.
   Corroborated passes; unrelated is ineligible; conflict/unclear require review.
   There is no tuned confidence threshold and consequently no calibration split.
5. Missing facts take precedence over disqualification; contradictory identities
   take precedence over both. Deterministic disqualifications need no model call.
6. Every vendor appears exactly once. Eligible records alone enter the shortlist,
   ordered by decimal price then vendor ID. Empty vendor input needs input.
7. A screening-only request completes when all records have decisions. Preparing
   contact for an eligible shortlist needs approval. No approval is inferred.
8. Overall status precedence: failed, needs_input, needs_review, needs_approval,
   completed. Completed rows remain visible in a partially unresolved request.
   A provider/contract failure is failed, never semantic uncertainty.
9. Code owns status, decisions, evidence IDs, shortlist, approval flags and actions.
   A semantic provider returns only verdict and supporting source IDs. It cannot
   generate or replace the business result. Summary is an exact, deterministic
   receipt for all arms; free-form prose cannot reverse the approval constraint.

## Two separate questions

**A — prepared execution.** Compare `agent_direct`, `agent_task_skill`, and
`prepared_runner` on the same case inputs, output contract and grader. The two
agents have the same model, tools, turn/token budgets and fresh contexts; both can
write and execute Python. The task Skill supplies procedure, not answers. Timing
starts before executor initialization and ends at the JSON result. Record model
calls, tool time, failures and usage. Record preparation as unknown unless metered;
do not infer lifetime savings from repeat-execution costs. Runner dispatch by an
external host agent is outside this boundary and must be measured separately.

**B — construction.** Compare `build_without_skill` and `build_with_skill`, using
the same model, task, development inputs (no labels), helper code, tools and build
budget. The only treatment is the repository WhatToOffload Skill and its referenced
design resources. Each receives a fresh isolated workspace and context. Both must
produce a JSON-stdin/JSON-stdout `candidate.py` plus an `offload_decisions.json` for
three workflow boundary probes. Freeze the candidate before any final input is
provided. Execute it on unseen cases with the same grader. No repairs during final
evaluation; human repair counts/time remain unknown until independently logged.
Report syntax/runnability, acceptance, boundary decisions, construction time/tokens/
cost, and post-build execution separately. Never substitute direct task execution
for the no-Skill construction arm.

No Jev-specific efficacy claim is made. One configurable semantic model adapter is
sufficient for this minimum experiment; adding a Jev ablation is a separate study.

## Isolation and leakage

Provider requests contain task/input only, never gold or grader. Agent tools run in
a network-disabled, resource-limited Docker container mounting only an allowlisted
temporary workspace; the repository, gold, tests, credentials and host paths are
not mounted. The host mediates model calls. All agents get the same tools. Merely
changing cwd is NOT isolation. Live agent/build experiments fail closed without
Docker. Offline fakes are explicitly simulations, not independent agents.

Build evaluation containers receive only candidate code, neutral helper, current
input and a JSON-lines semantic bridge; the host supplies the same model adapter
as the prepared runner. Candidate outputs are data, never imported by the grader.
Gold is a manually authored table with per-case rationales; the grader does not
import the runner or call its decision function. Gold consistency is checked
structurally and arithmetically against explicit facts, not by invoking the runner.

## Splits and freeze

Development cases and boundary tests may guide implementation. Final cases are
authored separately after the implementation is stable; they change actual
decision boundaries, not only identifiers. They include normal, missing,
contradictory, duplicate, noisy, policy-change and review cases. Two boundary probes
require retaining the agent (changing goals; one-off uncontractible negotiation).
The author is also the implementer: this is a prospective local holdout, not an
independent blind benchmark or protection against future public-data training.

Before final execution, write a manifest hashing runtime code, task, prompts,
grader, protocol, development data, final inputs and gold. Verify it before every
final run. Freeze each B candidate separately. Final data must not appear in build
workspaces. If final failures inform code/prompt/grader changes, retire that split
to development and author a new final version. Never refresh a freeze in place.
Offline development rehearsal is separate from the still-unexecuted formal final
model evaluation. Schema-only auditing of final gold is not an executor run.

## Metrics (unit = case × arm × repetition unless stated)

All scheduled attempts remain in results, including exceptions and budget stops.

| Metric | Numerator | Denominator |
| --- | --- | --- |
| Task correctness | Exact required structured decisions, statuses, shortlist, evidence and approval contract | All scheduled attempts |
| Wrong automatic release | Predicted eligible records whose gold is not completed/eligible | All predicted eligible records; undefined if none |
| Review rate | Rows returning needs_review | All expected vendor rows |
| Correct review recall | Gold review rows correctly returned for review | All gold review rows; undefined if none |
| Citation precision | Cited IDs allowed by that row's gold evidence | All cited IDs; undefined if none |
| Omission rate | Expected vendor rows absent from output | All expected vendor rows |
| Actual completion rate | Correct outputs with overall completed status | All scheduled attempts |
| Execution failure rate | Process/provider/contract failures | All scheduled attempts |

Also report correct needs_input/needs_approval counts, record decision accuracy,
and median wall time including failures. An all-review executor cannot obtain high
task correctness or actual completion. Missing cost/usage is null (unknown), never
zero. Offline provider spend is zero because no calls occur, but model performance
and production cost are unknown. Report simulated and live arms separately.
Keep every case result, error code, grading reason and call count. Reports and SVG
are generated from records; no fixed repeat count or success claim is embedded.

## Live gate and budgets

No live experiment is authorized by this protocol. CLI requires `--live`, explicit
configuration, an approved global request cap and a USD reservation ceiling. A
per-request conservative upper bound is reserved BEFORE each HTTP request (including
failed requests), based on configured input/output caps and supplied price bounds.
Stop all remaining attempts visibly when exhausted. Provider prices and model
capabilities must be verified before authorizing a live matrix. Tokens/cost that
cannot be measured remain unknown. No automatic retry hides failures or spend.

Historical microbenchmark defects and repairs concern its shipped Python harness.
They are not evidence about the unavailable private long-task runner.
