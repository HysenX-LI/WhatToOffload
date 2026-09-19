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

## Runner contract

- **Importable entry point:**
- **JSON CLI invocation:**
- **Configuration variables:** names only; never values
- **Caller-managed resume fields:**
- **Result-envelope statuses used:**

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
- Contract tests:
- Representative semantic cases:
- Composition-policy and uncertainty-routing tests:
- Uncertainty and review cases:
- Side-effect approval cases:
- Idempotency and unknown-outcome cases:
- Provider mocks:
- Focused and broader regression suites:
- Optional live probe requiring confirmation:

## User authorization boundary

State explicitly that this document is a design. Do not edit the target project until implementation has been authorized, unless autonomous implementation was already requested.
