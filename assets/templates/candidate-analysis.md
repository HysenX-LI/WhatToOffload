# Offload candidate analysis

## Evidence reviewed

- Sources inspected:
- Current workflow goal:
- Inputs available at decision time:
- Expected output and consumer:
- Side effects and accountable owner:
- Process-lifetime boundary, timers, external events, or human waits:
- Existing runtime, queue, database, and operational owner:

## Blocking questions

List only missing facts that materially change the recommendation. If any remain, stop before ranking candidates.

## Recommended candidates

Repeat the following card no more than three times.

### Candidate: `<bounded subflow name>`

- **Boundary:** `<start trigger>` → `<final result or handoff>`
- **Workflow class:** `short-lived bounded | durable asynchronous`
- **Why this class:**
- **Why offload:**
- **Atomic nodes:**
- **Likely executors:**
- **Concrete replacements:** `<observed behavior → proposed code/tool/Jev/LLM/retained agent>`
- **Replacement prerequisites and supporting evidence:**
- **Quality that must be preserved:**
- **Expected benefit:**
- **Capability or coverage potentially lost:**
- **Failure detection and recovery:**
- **Diagnosability:** current traces available, missing audit boundaries, and the minimum events needed to locate a regression
- **Broad-search policy, if applicable:** candidate generators, Jev-guided direction choice, context batching, exploration budgets, and stop conditions
- **Smallest comparison that could support or reject the replacement:**
- **Main risk or unknown:**
- **Expandable map:** `atomic nodes | complete subflow | both`

| Dimension | Assessment | Evidence |
| --- | --- | --- |
| Boundary clarity | high / medium / low | |
| Agent supervision removed | high / medium / low | |
| Replaceability | high / medium / low | |
| Reuse and frequency | high / medium / low | |
| Verifiability | high / medium / low | |
| Cost and latency | improves / mixed / worsens / unknown | |
| Implementation effort | high / medium / low | |
| Uncertainty | low / manageable / high / unknown | |
| Side-effect risk | none / gated / high | |

## Recommended order

Explain the trade-off. Do not calculate a synthetic total score.

## Keep in the current agent

| Node or responsibility | Why it should remain | What evidence could change this |
| --- | --- | --- |
| | | |

## Next decision

Ask the user to select one candidate for detailed workflow design, unless they explicitly authorized autonomous selection and implementation.
