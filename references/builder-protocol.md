# Capsule-driven implementation protocol

Use this protocol only after analysis and detailed design are complete, implementation is authorized, and every implementation decision needed by the builder is frozen.

## Separate decision work from construction

The analysis or design agent owns workflow boundaries, executor selection, public contracts, quality requirements, authorization scope, and accepted trade-offs. It emits an implementation capsule conforming to `assets/schemas/implementation-capsule.schema.json`.

The builder owns only the authorized file changes needed to realize that capsule. It must not rank offload candidates, select different executors, reopen accepted trade-offs, broaden the workflow, or infer unresolved product behavior.

Keep the human-readable design as the review record. The capsule is its compact implementation projection, not a replacement for design history.

## Prepare the builder handoff

Before starting implementation:

1. Validate the capsule with `scripts/validate_implementation_capsule.py`.
2. Confirm `unresolved` is empty and the authorization scope still matches the requested changes.
3. For a standalone Python runner, optionally materialize the versioned scaffold and generated contract tests with `scripts/materialize_bounded_runner.py` into a new empty directory. Use `--manifest-out` to keep a harness-owned manifest copy outside the builder directory.
4. Give the builder only:
   - the validated capsule;
   - the generated manifest and contract tests, when materialized;
   - files listed under `target.context_paths`;
   - the target files listed by the change plan;
   - the compact instructions in this protocol.

Do not give an isolated builder the full WhatToOffload Skill, candidate analysis, executor-selection discussion, rejected alternatives, or unrelated repository files. If no isolated builder is available, keep the capsule as the frozen contract in the current agent and do not reopen analysis unless a stop condition is reached.

## Builder procedure

1. Check that the target stack, paths, scaffold, components, commands, and dependencies match the capsule.
2. Read each context path once. Do not browse outside the declared context merely for orientation.
3. Modify only `target.allowed_changes`. Treat the generated tests, manifest, scaffold files, and declared immutable paths as read-only.
4. Use shared components for stable parsing, arithmetic, envelopes, CLI behavior, or other supplied primitives. Do not reimplement them in the domain file.
5. Implement the frozen nodes and public contract. Do not add optional architecture or speculative abstraction.
6. Run only the acceptance commands declared in the capsule, within `max_test_commands` and `wall_seconds`.
7. For a materialized standalone runner, finish with `scripts/verify_implementation_build.py <runner-root> --manifest <harness-manifest> --run-tests`. The external manifest prevents an accidental in-directory manifest edit from blessing changes to immutable files.

Measurement or harness bookkeeping should not consume the builder's tool or test budget. Record it outside the builder turn when possible.

## Stop instead of improvising

Return `needs_reanalysis` with a concise reason when:

- the capsule is invalid, contains an unresolved value, or contradicts itself;
- a declared target path, dependency, scaffold, component, or command is unavailable;
- the target project conflicts with a frozen public contract;
- a failing acceptance case exposes a missing product decision rather than an implementation defect;
- continuing would exceed a declared construction budget;
- the requested change would leave the authorized file or side-effect scope.

Do not resolve these conditions by reading the full Skill again or silently choosing a new workflow design.

## Completion evidence

A completed build reports:

- capsule and manifest identity;
- files changed;
- acceptance commands and results;
- immutable-file verification;
- measured wall time, tool calls, and test-command count when available;
- budget compliance;
- intentionally untested behavior and remaining construction risk.

Passing generated tests proves only the declared cases. Keep independent cases or a frozen comparison suite for consequential semantics, portability boundaries, and transfer evaluation.
