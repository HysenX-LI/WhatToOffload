# Codex supplier screening v2

CODEX MEASURED: ChatGPT authentication; GPT-5.6 Sol / high. Account billing cost unknown.

Run: `codex-v2-dev-execution-1`; split: `dev`; stop: `Codex_agent_timeout`.

One paired repetition is descriptive; no Jev/DeepSeek/cheap-model or population claim.

| Arm | Executed/planned | Correct/planned | Wrong release | Review | Actual completion | Median ms | Codex calls | Tools | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---:|---|
| agent_direct | 2/2 (100.0%) | 1/2 (50.0%) | 0/1 (0.0%) | 0/2 (0.0%) | 1/2 (50.0%) | 230312.087 | 2 | 9 | unknown/unknown/unknown |
| agent_task_skill | 1/2 (50.0%) | 1/2 (50.0%) | unknown | 0/2 (0.0%) | 1/2 (50.0%) | 68833.602 | 1 | 5 | 98875/71936/2555 |
| prepared_runner | 1/2 (50.0%) | 1/2 (50.0%) | unknown | 0/2 (0.0%) | 1/2 (50.0%) | 0.205 | 0 | 0 | 0/0/0 |

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
| agent_direct | dev-equality | completed | completed | True |  |
| prepared_runner | dev-price | completed | completed | True |  |
| agent_task_skill | dev-price | completed | completed | True |  |
| agent_direct | dev-price | failed | unknown | False | output must be an object; vendor coverage mismatch; Codex_agent_timeout |
| agent_task_skill | dev-equality | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
| prepared_runner | dev-equality | not_executed | unknown | False | output must be an object; vendor coverage mismatch; interrupted_or_not_executed |
