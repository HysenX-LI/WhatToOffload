# Test-driven workflow implementation

Read this playbook only after an offload candidate reaches detailed design or implementation. It turns a workflow specification into small, observable red-green-refactor slices without imposing a particular language or test framework.

## Treat tests as the executable boundary

Start from externally meaningful behavior:

- accepted input and structured output;
- result-envelope status and required action;
- state transition and terminal outcome;
- uncertainty, missing-input, approval, and failure routes;
- external calls prepared or suppressed;
- idempotency, retry, timeout, cancellation, and recovery behavior where applicable.

Prefer tests at the narrowest public seam that proves the behavior. Avoid asserting private call order, internal helper names, exact generated prose, or other incidental structure.

For a non-code SOP or early workflow design, first express these as named examples with input, expected observable outcome, and prohibited side effects. Make them executable when implementation begins.

## Establish a test seam

Before the first implementation slice, identify how tests will control dependencies:

- use the target project's existing test runner and fixture style;
- inject or wrap clocks, random values, identifiers, model clients, HTTP clients, queues, storage, and side-effect APIs;
- use in-memory or project-standard fakes when behavior matters;
- use mocks only at stable external boundaries and assert outcomes rather than every internal call;
- keep fixtures small, explicit, synthetic, and free of credentials or sensitive production data.

Do not add a parallel test framework merely for the generated runner. If the project has no test environment, propose the smallest compatible choice and treat that as an implementation decision.

## Use the red-green-refactor loop

For each behavior slice:

1. **Red:** write one smallest meaningful test and run it. Confirm the failure is caused by the missing or incorrect behavior, not syntax, fixture, import, network, or environment failure.
2. **Green:** implement only enough production behavior to pass the new test without breaking the existing suite.
3. **Refactor:** improve names, boundaries, duplication, and composition while the suite remains green.
4. **Record:** retain the test as regression protection and move to the next risk-ranked behavior.

If a newly written test passes before implementation, determine whether the behavior already exists, the test is ineffective, or the test is observing the wrong seam. Do not count it as the red phase without resolving that ambiguity.

Run focused tests during each slice and the proportionate broader suite before handoff. Never weaken an assertion only to obtain green without explaining the changed contract.

## Start with characterization for existing workflows

When replacing or refactoring an existing agent loop, prompt-and-parse step, script, or integration:

1. capture representative current inputs and observable outputs;
2. write characterization tests for behavior that must remain compatible;
3. mark accidental, unsafe, or intentionally changed behavior explicitly rather than preserving it silently;
4. add the new desired acceptance test and observe it fail;
5. change one boundary at a time.

Characterization tests protect known behavior; they do not certify that the old behavior is correct.

## Cover the workflow in layers

Choose only the layers needed for the selected risk profile:

| Layer | What it proves |
| --- | --- |
| Contract | Inputs, envelopes, schemas, status values, versioning, and safe diagnostics remain compatible. |
| Activity unit | A deterministic transform, tool adapter, judgment composition, or action preparation behaves correctly in isolation. |
| Semantic case set | Representative Jev or LLM inputs lead to acceptable policy outcomes, escalation, or review. |
| Transition | Events and activity results move the workflow to the correct next or terminal state. |
| Integration | The project adapter works with a local fake, sandbox, or mocked provider boundary. |
| End to end | The smallest complete path produces the intended observable result without unintended effects. |

Do not pursue a coverage percentage as a substitute for risk coverage. Prioritize consequential branches, ambiguity, recovery paths, and previously observed failures.

## Test semantic nodes without brittle snapshots

Separate three concerns:

1. **Request and response contract:** deterministic tests verify the state shape, question or prompt version, accepted schema, parsing, and error mapping with a provider fake.
2. **Composition policy:** deterministic tests feed structured answers and probabilities into code, then verify thresholds, routing, review, and action suppression.
3. **Model behavior:** a versioned representative case set checks whether the selected provider/model produces acceptable application outcomes.

For Jev Choice, Noul, or Score, test that code handles valid options, probability fields, confidence where applicable, uncertain cases, and no-match policy. Do not require one exact probability unless the value comes from a fake specifically created for the composition test.

For generated LLM text, prefer structural requirements, required evidence references, prohibited claims, and human-meaningful evaluation criteria over exact-string snapshots.

Keep real provider evaluations separate from the default suite. They require explicit confirmation, controlled cost, non-sensitive inputs, recorded provider/model versions, and a report that distinguishes contract failure from model-quality failure.

## Validate extraction and batch completion

For workflows that assemble records from external sources, test the boundary between partial evidence and a deliverable result:

- **Optional data:** a missing optional field or link must not abort unrelated records. Exercise the configured recovery route and preserve explicit unknowns; keep missing required input and unresolved required sources visible in status.
- **Model output:** validate the application schema as well as JSON syntax before advancing. Cover truncated responses, missing envelopes and invalid field types. Use bounded retries; accept a format-only normalization only when it has one unambiguous interpretation and preserves every fact.
- **Evidence:** retain complementary observations from the same canonical source. Verify a value against retrieved evidence and the intended entity, not just a matching string somewhere in the document. A discovered link can be supported by its referring page; it does not prove ownership by itself.
- **Candidate preparation:** preserve labels, local context and source ownership when extracting candidates. Cover standard encodings and link schemes; group duplicate values before asking a Choice question while retaining their supporting sources. Do not manufacture confidence by adding probabilities for duplicate options after inference. Diagnose missing candidates and lost context before attributing a failure to Jev or lowering a threshold.
- **Assertions:** keep rejected claims in an audit record, not in populated output fields. An executor returning `completed` does not prove semantic acceptance. Measure missing entities, available-field recall, asserted-field precision, evidence and required artifacts separately.

Keep Jev decisions narrow enough to preserve the relevant context within provider limits; splitting evidence must not remove the identity or relationship that the question asks it to verify.

For a Jev-first cascade, prove that accepted normal cases and confident no-match results make no stronger-model calls. Test that uncertainty or a candidate-coverage failure triggers only the affected fields, that fallback output cannot overwrite accepted fields, and that unsupported fallback values remain unresolved. Record escalation counts and reasons during live evaluation so an unconditional LLM dependency cannot masquerade as an exception route.

A no-match test must state the searched scope and whether retrieval is complete enough for the required outcome. Exercise the difference between an unsupported parser, a failed fetch, incomplete candidate coverage, and genuine ambiguity; they need different recovery actions. A high-confidence selection cannot compensate for a missing correct candidate.

When evaluating a replacement, retain the old-versus-new result on common inputs as well as the complete workflow result. Check the capability at risk, not only the faster or cheaper branch. Attribute regressions to retrieval, candidate preparation, context, judgment, routing, or validation. Report fallback's additional validated outcomes and its escalation denominator; fewer calls alone do not establish better routing. Keep the declared quality boundary fixed unless the user explicitly accepts a different trade-off.

When measuring transfer to new inputs, freeze the workflow before selecting the evaluation case. Retain every initial outcome. Once a case informs a repair, label subsequent runs as post-inspection tests and do not present them as untouched hold-out results. Compare execution cost only alongside the declared quality gate, and distinguish measured provider spend from unpriced calls and workflow construction cost.

## Test approvals and side effects before enabling them

Use a fake effect sink or sandbox adapter to prove:

- no side effect occurs on `needs_input`, `needs_review`, `needs_approval`, or `failed`;
- the prepared action contains the expected target and safe payload;
- approval is scoped, authenticated where applicable, unexpired, and bound to the current state;
- rejection and stale approval leave the effect unexecuted;
- repeated delivery reuses the logical idempotency key;
- timeout with an unknown outcome reconciles before retry;
- diagnostics and logs contain no secrets or unnecessary source data.

The first live side-effect test remains a separate authorization boundary even when all fake-based tests pass.

## Add durable-workflow tests when applicable

Use a deterministic or virtual clock and the target runtime's test harness where available. Cover:

- restart or replay at every checkpoint;
- duplicate, missing, delayed, and out-of-order events;
- concurrent resume attempts and stale state versions;
- timer firing, reminder timing, backoff, and retry exhaustion;
- cancellation before, during, and after an activity;
- approval expiry and state changes while waiting;
- workflow-definition and persisted-state migration;
- unknown external-effect outcome and reconciliation;
- stuck-workflow detection and visible operational escalation.

The same logical event replayed from the same initial state should produce the same transition decisions, except for explicitly injected time, identity, or provider results.

## Define completion evidence

An implementation handoff should report:

- the behaviors added or changed;
- the test that was observed failing for each meaningful slice, summarized rather than dumping logs;
- the focused and broader suites run after implementation;
- semantic case-set results and review rate when model behavior was evaluated;
- tests intentionally deferred and the remaining risk;
- any live provider or side-effect test that still requires confirmation.

Passing tests are evidence for the tested contracts, not proof that every workflow input or external service will behave correctly.
