# Codex supplier screening v2

SIMULATION ONLY: software regression; no model evidence.

Run: `codex-v2-offline-dev-2`; split: `dev`; stop: `None`.

One paired repetition is descriptive; no Jev/DeepSeek/cheap-model or population claim.

| Arm | Executed/planned | Correct/planned | Wrong release | Review | Actual completion | Median ms | Codex calls | Tools | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---:|---|
| prepared_runner | 10/10 (100.0%) | 10/10 (100.0%) | 0/5 (0.0%) | 2/11 (18.2%) | 5/10 (50.0%) | 0.0325 | 0 | 0 | 0/0/0 |

Cached input is included in input tokens. Startup/context/return time included; grading excluded.
Additional metrics with numerators, denominators and token completeness are in report.json.
Prepared runner/task Skill preparation and required human rework are unknown. Billing is unknown, not zero.

## Construction investment (separate from execution)

| Arm | Status | Syntax | Runnable | Correct | Boundary decisions | Build ms | Calls | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---|

Construction was not executed.

## Every scheduled attempt

| Arm | Case | Execution | Status | Accepted | Failure reasons |
|---|---|---|---|---|---|
| prepared_runner | dev-equality | completed | completed | True |  |
| prepared_runner | dev-duplicates | completed | completed | True |  |
| prepared_runner | dev-unclear | completed | needs_review | True |  |
| prepared_runner | dev-price | completed | completed | True |  |
| prepared_runner | dev-no-reference | completed | completed | True |  |
| prepared_runner | dev-contact | completed | needs_approval | True |  |
| prepared_runner | dev-dispute | completed | needs_review | True |  |
| prepared_runner | dev-missing-currency | completed | needs_input | True |  |
| prepared_runner | dev-unrelated | completed | completed | True |  |
| prepared_runner | dev-partial | completed | needs_input | True |  |
