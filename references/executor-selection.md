# Executor selection

Assign an executor only after the workflow boundary and required behavior are clear.

## Work through a replacement

Use this procedure to turn observed agent work into defensible substitutions. During analysis, complete steps 1–3 at the level supported by available evidence; mark unmeasured benefits as hypotheses. Complete the contracts and experiment plan for a selected design. Execute experiments and implementation only within the user's authorization. Scale the detail to material trade-offs rather than creating a card for every trivial operation.

### 1. Observe the behavior being replaced

Trace a representative input through the current workflow. Identify the action, information used, output, and why another step was needed. Split broad labels such as “research” or “extract” into observable behaviors: enumerate candidates, verify ownership, choose a value, discover another source, or assemble an artifact.

Separate stable repetition from adaptation. A known fetch/parse/merge sequence can become code; inventing a new search strategy when the known sources fail may still require an LLM or the current agent. Include conversational context and implicit assumptions that the replacement would otherwise lose.

**Record:** current behavior → explicit input → observable output, with evidence from a trace, code, SOP, or representative case. If no execution trace exists, do not invent call counts or savings.

### 2. Define the quality boundary before optimizing

Specify what must remain true for the downstream consumer: required coverage, precision, evidence, artifact validity, and acceptable unresolved cases as applicable. Use the task's actual requirements; do not import a universal score or confidence threshold. Record any explicitly accepted trade-off rather than silently lowering quality to save cost.

**Record:** acceptance criteria, costly failure modes, and the baseline behavior. Process completion and semantic acceptance are separate outcomes.

### 3. Compare concrete substitutions

Use the executor table below to identify the simplest sufficient implementation. Compare credible alternatives where the choice matters; retaining the current executor is a valid option.

| Substitution | Useful when | What it can lose | Evidence needed before adopting it |
| --- | --- | --- | --- |
| Agent/model operation → code or existing tool | Rules, supported formats, calculation, retrieval steps, or artifact assembly are explicit | Adaptation to unfamiliar structures or unanticipated paths | Coverage of supported inputs, detection of unsupported ones, and a recovery route |
| Agent/LLM judgment → Jev | The decision is narrow and the supplied state supports typed selection or verification | Open-ended discovery, generation, and context omitted from the state | Candidate coverage, relevant context, representative decision outcomes, and calibrated routing |
| Broad agent search loop → code/tool discovery plus Jev-guided bounded exploration | Candidate generators can expose plausible directions and the value of following each one can be judged from supplied context | Search strategies and sources absent from the generated frontier | Candidate coverage, context-preserving batches, page-expansion outcomes, explicit budgets, and unresolved results after exhaustion |
| Broad agent loop → bounded LLM node | Generation, interpretation, or a change of search strategy remains necessary | The agent's wider tools, memory, goal negotiation, and ability to keep exploring | Explicit context and tools, constrained output, useful recovery outcomes, and stopping rules |
| Keep current agent or human | Goals change, context cannot be supplied, or responsibility cannot be delegated | Potential savings from automation | Why the boundary is not yet stable and what evidence could change that decision |

**Record for each material replacement:** old behavior → proposed executor; prerequisites; expected benefit; capability or coverage at risk; detection/recovery; and the experiment that would support or reject the choice. Do not require Jev for deterministic work or force open-ended discovery into a fixed candidate choice.

### 4. Specify the evidence passed across the boundary

Define the state the replacement actually receives. For candidate-based decisions, retain canonical value, source, local context, relevant labels, and entity ownership. Group duplicate values before inference while preserving supporting evidence. Bound payloads by selecting relevant evidence; do not truncate away identity or relationships simply to fit a size limit.

Keep candidate coverage separate from selection confidence. A confident no-match says that the supplied candidates do not match; it does not establish absence from unsearched sources. Distinguish not searched, retrieval failed, not found within the searched scope, ambiguous, and verified when these states change the next action. The containing runner can still use its existing result envelope.

For a large search space, define how code or tools generate candidates, how context-sized Jev calls choose promising directions, how results compose across batches, and how the runner bounds breadth and depth. Follow [Jev-guided bounded exploration](jev-guided-exploration.md); do not compare conditional Choice probabilities from disjoint option sets as if they shared one denominator.

**Record:** evidence contract, supported input scope, coverage checks, and the meaning of missing or unresolved output.

### 5. Design recovery for the capability being lost

Route the cause of failure rather than every empty value to a stronger model. A parser failure needs repair or an alternate parser; insufficient evidence needs bounded retrieval; ambiguous supplied evidence may need a stronger judgment; an unfamiliar search path may need LLM planning. Model synthesis cannot establish a fact absent from its evidence.

Use the explicit exception branch below when code and Jev cover the normal path. Specify affected fields or decisions, available tools, attempt/time/cost limits, stopping conditions, and the outcome after exhaustion. Preserve accepted work and unrelated records. If exceptions dominate representative inputs, reconsider the executor or workflow boundary rather than weakening acceptance.

**Record:** trigger → recovery action → validation → stop or handoff, with the reason visible in diagnostics.

### 6. Test one substitution before composing many

Compare old and proposed behavior on the same representative inputs and quality criteria. Include ordinary cases, supported variations, insufficient evidence, and a case outside the proposed executor's scope. Use captured inputs for controlled comparisons where possible; keep live end-to-end runs to expose retrieval and integration effects. Do not feed reference answers to the executor.

Attribute failures to retrieval, parsing/candidate preparation, lost context, model judgment, routing, or output validation before changing prompts or thresholds. Check contracts with fakes and semantic behavior with representative cases; neither alone establishes task quality. Follow [test-driven-workflows.md](test-driven-workflows.md) for authorized implementation.

**Record:** measured gains and losses, unresolved causes, and a decision to adopt, revise, or retain the original behavior. A passing local probe is not evidence that full-task coverage improved.

### 7. Measure the composed workflow and revisit the balance

Run the complete path against the same acceptance criteria. Report coverage and correctness alongside model spend, wall time, retrieval, retries, and any remaining agent supervision. Measure escalation per eligible decision or record with an explicit denominator, not just the absolute LLM call count. Track whether fallback produced additional validated outcomes; an escalation that returns unknown may still be correct, but is not recovered coverage.

For performance, account for evidence preparation, normal decisions, exception frequency and cost, validation, and orchestration. Inspect the critical path: parallel request durations do not sum to wall time. Batch independent questions sharing evidence when it preserves context; avoid replacing one broad call with many unnecessary serial calls.

Adopt the change when it meets the declared quality boundary and offers a useful cost, latency, supervision, or maintainability trade-off. Report a quality regression as a trade-off, not successful-task savings. Separate recurring execution cost from construction and maintenance effort; estimate payback only when reuse volume and build cost are known. Evaluate new inputs independently before claiming generalization.

**Deliver:** the replacement map, measured comparison, and remaining boundaries. Keep private task identities and raw evidence out of reusable skill instructions and public examples.

## Record two independent decisions

For every node, record:

1. **Execution location:** current agent or external runner.
2. **Executor:** capability role plus concrete implementation.

Offloading a node does not imply using Jev. A runner can contain ordinary code, tools, one or more model adapters, and approval handoffs.

## Choose the simplest sufficient executor

| Capability role | Use when | Avoid when |
| --- | --- | --- |
| Deterministic code | Rules, parsing, calculations, exact lookup, validation, composition, retry, or control flow are explicit | The decision requires semantic interpretation that rules cannot express reliably |
| Existing tool or API | A supported system already owns the data or action | The integration is unavailable, unauthorized, or less reliable than a local function |
| Jev | The node is a narrow typed judgment over supplied state and code can act directly on Choice, Noul, or Score output | The node must generate prose, plan, invoke tools, or perform broad multi-step reasoning |
| Smaller LLM | The node needs bounded generation, extraction, or transformation and representative tests show adequate quality | Errors are high-cost or the task consistently needs deep reasoning |
| Stronger LLM or external agent | The task needs open-ended synthesis, generation, planning, or tool-mediated reasoning | A cheaper and more testable executor is already sufficient |
| Current agent | The work depends on live conversation, changing goals, broad exploration, or local coordination that is not yet contractible | The same stable loop repeats and can receive explicit context |
| Human | Responsibility, policy, taste, high-impact ambiguity, or irreversible action requires accountable review | The decision is routine, low-risk, and validated for automation |

Do not treat Python, TypeScript, or another language as a capability role. Record language and library choices under concrete implementation.

## Jev selection

Jev is a candidate when code needs programmable semantic judgment:

- **Choice:** pick one member of a known set; include a no-match option when coverage is not guaranteed.
- **Noul:** estimate whether one defined condition is true; use separate questions when multiple labels may apply.
- **Score:** place an item along ordered, concretely described levels.

Keep deterministic rules and side effects in code. Split broad judgments into focused questions, batch independent questions over the same state, and combine their outputs in code.

When Jev guides a broad information search, it should judge supplied directions or whether a page is worth expanding while code owns candidate generation, fetching, the exploration frontier, visited-source tracking, budgets, and stopping. Use [Jev-guided bounded exploration](jev-guided-exploration.md) to preserve candidate coverage and compose multiple context-bounded calls correctly.

Before specifying Jev requests or code, read the current `typesafe-ai` skill and its routed live documentation. This playbook intentionally does not duplicate SDK or HTTP payload details.

## Keep stronger models on an explicit exception branch

When code and Jev are sufficient for the normal path, let their accepted result complete that path. Do not add an unconditional LLM review after each Jev decision, or make a reasoning model perform every extraction before Jev checks it.

For source extraction, code can enumerate candidate values and preserve their evidence; Jev selects or verifies their meaning and ownership. Check candidate coverage as well as selection confidence. A confident no-match can be a valid missing value: fetch additional evidence through the bounded retrieval policy when appropriate, rather than automatically escalating every empty optional field.

Invoke the stronger model only for a recorded exception, such as uncertain selection, conflicting evidence, an unsupported source structure, or a demonstrated gap in candidate coverage. Send the affected fields and relevant evidence, preserve already accepted fields, and validate any replacement values before merging them. Bound the fallback and leave unresolved values explicit when its budget is exhausted.

Measure model calls by route, escalation reasons and rate, token usage, and end-to-end latency alongside quality. A high escalation rate is a signal to inspect evidence preparation, candidate coverage and task fit; it is not a reason to weaken the acceptance gate. Keep deep reasoning on the cases that need it rather than enabling it indiscriminately for ordinary parsing.

## Ordinary LLM selection

Use an LLM for capabilities such as:

- drafting or rewriting prose;
- summarizing selected evidence;
- open-ended synthesis across sources;
- planning that cannot be expressed as a fixed decision surface;
- recovery from a case outside a smaller executor's validated envelope.

For generated runners, describe an OpenAI-compatible adapter with configurable base URL, model, and API-key environment variables. Probe required capabilities instead of assuming that all compatible providers support Responses, tool calling, structured outputs, streaming, or reasoning parameters.

## Skill routing

At detailed-design time, inspect the skills actually available in the current environment. Use a relevant skill when it provides maintained, non-generic guidance for a node or artifact.

Record the handoff:

```yaml
skill_handoff:
  requested: typesafe-ai
  status: available | missing | unknown
  purpose: design and implement the selected Jev judgments
  fallback: read current official TypeSafe documentation
```

Do not assume a skill exists based only on this example. Do not copy a professional skill into WhatToOffload.

## Alternatives and experiments

When multiple executors are plausible, recommend one and preserve alternatives. State what evidence would change the choice. For an unvalidated semantic node, define a small comparison using representative examples, expected outcomes, latency, cost, uncertainty, and escalation rate.
