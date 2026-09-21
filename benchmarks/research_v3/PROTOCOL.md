# Prospective research v3.1 — registered before new final execution

Two separate descriptive studies. GPT-5.6 Sol/high, fresh ChatGPT-authenticated
Codex CLI only. No independent API, API key, purchase, reset or model fallback.
Reuse the frozen v2 runtime's tested OS filesystem/network isolation, not its task
prompts. Each context has only its own public materials/artifacts; no evaluator,
gold, sibling workspace, parent conversation or host skills. Run script candidates
under the same OS sandbox. Preflight must pass before any model invocation.

## Budget and order

Development: at most 8 Codex invocations, 1200 elapsed seconds. Formal: at most 48
invocations, 4800 elapsed seconds. This round totals at most 56 invocations and 6000
seconds of experiment runtime (offline engineering excluded). Per invocation:
semantic/review 120 s, design/agent execution 240 s, implementation/debug 300 s;
40 CLI-reported tool items; script execution 30 s per case. Reserve failed calls.
Global deadlines include setup, tools, process launch, context transfer and return.
No harness retries; bounded CLI reconnects remain inside their original timeout.
Quota, provider-terminal and global caps stop the run and save
all remaining entries as not_executed. In the formal study, a per-call timeout or
tool/output cap ends that invocation and records a failed phase; continue unrelated
arms within the original total budget, without retrying that invocation. A build
with any failed phase is incomplete: retain its artifacts, but do not count partial
code as a successful build or expose it to final execution. Script/schema/quality failures are retained
and do not stop unrelated cases. No automatic repair after final exposure.

First offline regression, then two independent model annotators on semantic DEV
pairs (rules/materials only, no gold or each other's responses), and a small raw
workflow development construction/execution probe. Compare their judgments only
AFTER both return. Author labels are not independent human annotation. Resolve rule
ambiguity only on development evidence. Freeze sources, prompts, rules, scorer,
config, fixtures, treatment resources and v2 runtime before new final execution.
Old public_v1 final is exposed regression, including the disputed case; do not
modify any old gold, scores, results or freezes. New final author has seen labels;
'unseen' means prospectively withheld from builders/executors, not author-blind.

## S1 semantic boundary

Use SEMANTIC_RULES.md verbatim in BOTH full task and bounded node. Pair families
change one decision-bearing statement: project linkage; denial vs missing evidence;
full vs partial support; known other work vs unlinked denial. Final is a separately
written transfer set (tuple linkage, policy component requirements, quoted claims
and missing positive project identity); not just renamed development inputs. Freeze before models
see final. Two fresh model reviewers classify the final material blind to gold,
then compare agreement/disagreements without changing labels or scores.

Compare direct Codex full-task execution with prepared deterministic code plus
bounded Codex. One repetition per case; alternate arm order. Both may use normal
local tools. Literal independently authored expected outputs are graded by existing
v1 evaluator (no shared business decision function); a second gold audit checks
schema, arithmetic and coverage. Invalid returns fail; protected fields can only
be supplied by code in prepared arm. Missing measurements null, never zero.
Report exact task and row correctness; reviews, correct reviews and conservative
reviews (predicted review where gold resolves); wrong release / predicted eligible
AND / gold noneligible; correct approval handoffs / expected approval; correct
business completion / expected completed; coverage, omissions and citations.
All-review loses resolved-case acceptance and completion. Review agreement is model
agreement with declared rules, not proof of objective truth or human annotation.

## S2 raw workflow design

Three separately authored synthetic workflow packets: repeat inventory reconciliation,
release event handoff, and a one-off relationship-sensitive response. Packets contain
SOPs, logs, requests, sample source files and existing imperfect scripts. They contain
no node graph, executor allocation, mandated semantic interface or implementation.
Builders may select whole/partial offload, retain Agent, or implement any architecture.
The observer's JSON result/file invocation contract only permits common external
testing. Keep-agent is an eligible outcome and never fails merely for lacking code.

Each workflow: same raw packet, observable acceptance document, dev inputs without
answers, Python/system tools, design budget and optional implementation budget.
Only treatment adds WhatToOffload SKILL.md and its existing related resources.
No forced reading in control. Treatment is instructed to consult the supplied Skill;
actual successful file-reading events and self-reported resources are recorded,
not credited as application quality. Same model/effort, isolated fresh workspaces.

A design call writes design.md and decision.json (implemented, agent_assisted or
keep_agent). An implementation call is allowed only if the design chooses it; it
may build any local architecture. The design can retain a Codex step via the
agent_assisted mode; its later execution is a fresh bounded Codex invocation with
frozen artifacts. Optional one debug call is allowed only after a DEV smoke failure,
using identical feedback policy. Freeze candidate artifacts before exposing ANY
final inputs; no cross-arm artifacts or final scores during design/build/debug.
Keep-agent later executes using its own frozen plan on the same final inputs.
Scripts run one case per fresh sandbox; Codex modes see one batch per workflow,
so within-batch cases are NOT independent calls. No prescribed runner/control flow.

Order: inventory control then treatment; release treatment then control; one-off
control then treatment (three pairs cannot be exactly balanced). Anonymous reviews
reverse this order. Artifact reviewer sees only raw packet, rubric and sanitized
own design/code, never arm labels, resource-read logs, gold or final outcomes.
Remove treatment names/paths and omit lines mentioning Skill/provenance/treatment using a preregistered
redaction; structural writing style may still reveal treatment, so blinding is
imperfect. One fresh model reviewer per candidate; no statistical-significance claim.

Rubric dimensions each 0/1/2 with quoted file evidence: boundary selection,
necessary context, executor fit, exception/approval handoff, implementation/operational
feasibility. Anchors are in RUBRIC.md. Report model ratings separately from deterministic
acceptance. No points merely for a runner, diagram or reading Skill. External grading
uses literal expected fields and safety checks, independent of internal architecture.
No build/review access to hidden answers/final input. Human rework not measured.

Design, implementation, explicit debug and subsequent execution have separate wall
and call/usage records. Debug internal to an implementation call cannot be separated:
its wall/tokens are unknown; implementation includes that work. Cached tokens are
reported subsets of input. Billing unknown. CLI tool events are observed counts;
underlying internal model requests are unknown. One build per arm/workflow, one
execution per final case; cross-workflow variation is not repeated-build variance.
Accept no or negative gain. Only this Codex setting is tested, not Jev/DeepSeek or
cheaper models. Preserve v2's no-observed-Skill-build-gain conclusion separately.

### Development amendment before final freeze

The first development construction hit its 300 s hard timeout after writing partial
artifacts. Preserve that failed run and its two completed, mutually agreeing model
annotations. The second explicit development probe uses fresh builder contexts with
a shorter-scope build prompt (target 200 s; hard cap unchanged). It reuses ONLY the
completed annotation evidence for the evaluator, never in builder prompts. Across
both development runs enforce at most 8 calls and 1200 measured runtime seconds;
the second invocation subtracts the first run's calls and rounded-up elapsed time.
This is an observed-development protocol amendment, not an automatic model retry or
a post-final adjustment. Final arms both receive the same amended prompt. A repeat
of this continuation cannot extend the registered round; no further live development
runs are authorized by this protocol if the combined cap is exhausted.

The initial un-frozen semantic final draft was inadvertently exercised by an
always-review offline countertest on three rows. No live model saw it, but the
whole draft is conservatively retired into `data/semantic/exposed-draft/` and its
exposure is recorded there. The prospective final was replaced BEFORE any formal
run with distinct boundaries (client/deliverable/engagement tuple linkage, policy
component requirements, quoted-claim linkage, missing project identity). Regression
countertests now use DEV only; final auditing checks schema/coverage without running
the task executor. This is not a renamed/reseeded draft and no old score is revised.

Formal stopping amendment: the development timeout motivated separating per-call
failures from quota/global exhaustion, before formal freeze. This prevents one slow
arm from suppressing the other workflows. No extra model retry or budget is added;
failed construction remains failed even if partial code happens to run.
