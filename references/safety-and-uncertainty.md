# Safety and uncertainty

Use this playbook whenever the selected subflow includes model judgment, credentials, an external API, or a side effect.

## Normal-path automation

Automation does not require pretending every input is easy. A good Phase 1 workflow automates the validated normal path and exits cleanly on detectable exceptions.

- High-enough confidence for the action and risk: continue automatically.
- Ambiguous semantic result: return `needs_review` with compact evidence and leading alternatives.
- Missing source data: return `needs_input` with the exact requested fields.
- Consequential side effect: return `needs_approval` before performing it.
- Service, code, or contract failure: return `failed` with safe diagnostics.

Never continue merely because one option has the highest probability.

## Decide whether a judgment is automatable

Build a representative case set before enabling automatic action. Measure application behavior, not exact wording or one demo probability.

Check:

- accuracy or agreement against expected outcomes;
- coverage of valid no-match and multi-label cases;
- whether uncertainty is identifiable;
- review rate on ordinary and edge inputs;
- error cost by action;
- missing-evidence failures versus model failures;
- sensitivity to threshold changes.

If review is frequent, first improve evidence, question boundaries, candidates, or composition. If the normal path remains ambiguous, keep the node in the current agent or human process.

Jev Choice and Score confidence describe concentration of the returned distribution, not end-to-end correctness. Noul has no separate confidence; values near 0.5 are uncertain. Calibrate thresholds using the target domain and action risk.

## Side effects and approval

Separate judgment from action. A workflow may prepare a write, send, purchase, deletion, permission change, or external message, but it must return `needs_approval` before the effect unless the user has granted a specific, valid approval for that action.

The approval request should state:

- the exact action and target;
- the material data that will be sent or changed;
- whether the action is reversible;
- the result that led to the action;
- what will happen after approval.

Do not broaden authorization from one action to another.

## External calls

Static checks and mocks are the default. Immediately before a live Jev, LLM, paid, or data-transmitting API call, obtain explicit confirmation unless the user already authorized that precise live test or operation in the current task.

Use the smallest non-sensitive synthetic payload that verifies the required interface. Report provider, endpoint class, model identifier returned by the service, response shape, latency, and sanitized usage or cost when available. Never report the key.

## Credential handling

- Prefer an existing ignored environment file, process environment, or secret manager.
- Do not copy secrets between projects for convenience.
- Do not embed secrets in command text, source, examples, fixtures, snapshots, logs, diagnostics, traces, or returned resume state.
- Redact authorization headers and key-shaped values from captured output.
- Keep credentials server-side for web or client applications.

If a key was pasted into a chat or other durable log, recommend rotation after the test. Do not repeat the value.

## Retry and failure

Retry only errors that are both transient and safe to repeat. Bound retries by attempt count or elapsed time. Respect rate-limit guidance when present. Do not retry side effects unless the operation is idempotent or has an explicit idempotency key.

Diagnostics should identify the failing node, stable error code, retryability, and sanitized message. Do not include raw provider bodies when they may contain source data or secrets.

