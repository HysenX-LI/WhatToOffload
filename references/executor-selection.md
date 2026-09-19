# Executor selection

Assign an executor only after the workflow boundary and required behavior are clear.

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

Before specifying Jev requests or code, read the current `typesafe-ai` skill and its routed live documentation. This playbook intentionally does not duplicate SDK or HTTP payload details.

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

