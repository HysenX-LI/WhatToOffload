# Codex supplier screening v2

CODEX MEASURED: ChatGPT authentication; GPT-5.6 Sol / high. Account billing cost unknown.

Run: `codex-v2-dev-integrated-3`; split: `dev`; stop: `Codex_transport_or_quota_failure`.

One paired repetition is descriptive; no Jev/DeepSeek/cheap-model or population claim.

| Arm | Executed/planned | Correct/planned | Wrong release | Review | Actual completion | Median ms | Codex calls | Tools | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---:|---|
| agent_direct | 0/2 (0.0%) | 0/2 (0.0%) | unknown | 0/2 (0.0%) | 0/2 (0.0%) | None | 0 | 0 | 0/0/0 |
| agent_task_skill | 0/2 (0.0%) | 0/2 (0.0%) | unknown | 0/2 (0.0%) | 0/2 (0.0%) | None | 0 | 0 | 0/0/0 |
| build_with_skill | 0/2 (0.0%) | 0/2 (0.0%) | unknown | 0/2 (0.0%) | 0/2 (0.0%) | None | 0 | 0 | 0/0/0 |
| build_without_skill | 0/2 (0.0%) | 0/2 (0.0%) | unknown | 0/2 (0.0%) | 0/2 (0.0%) | None | 0 | 0 | 0/0/0 |
| prepared_runner | 0/2 (0.0%) | 0/2 (0.0%) | unknown | 0/2 (0.0%) | 0/2 (0.0%) | None | 0 | 0 | 0/0/0 |

Cached input is included in input tokens. Startup/context/return time included; grading excluded.
Additional metrics with numerators, denominators and token completeness are in report.json.
Prepared runner/task Skill preparation and required human rework are unknown. Billing is unknown, not zero.

## Construction investment (separate from execution)

| Arm | Status | Syntax | Runnable | Correct | Boundary decisions | Build ms | Calls | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---|
| build_with_skill | failed | False | 0/2 | 0/2 | 0/3 | 392276.874 | 1 | unknown/unknown/unknown |
| build_without_skill | completed | True | 0/2 | 0/2 | 3/3 | 429054.218 | 1 | 329557/297600/21900 |

## Every scheduled attempt

| Arm | Case | Execution | Status | Accepted | Failure reasons |
|---|---|---|---|---|---|
| agent_direct | dev-equality | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| build_with_skill | dev-equality | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| prepared_runner | dev-price | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| agent_direct | dev-price | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| build_without_skill | dev-price | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| build_without_skill | dev-equality | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| agent_task_skill | dev-price | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| agent_task_skill | dev-equality | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| prepared_runner | dev-equality | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| build_with_skill | dev-price | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
