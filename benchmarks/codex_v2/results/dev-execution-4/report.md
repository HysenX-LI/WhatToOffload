# Codex supplier screening v2

CODEX MEASURED: ChatGPT authentication; GPT-5.6 Sol / high. Account billing cost unknown.

Run: `codex-v2-dev-execution-4`; split: `dev`; stop: `None`.

One paired repetition is descriptive; no Jev/DeepSeek/cheap-model or population claim.

| Arm | Executed/planned | Correct/planned | Wrong release | Review | Actual completion | Median ms | Codex calls | Tools | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---:|---|
| agent_direct | 2/2 (100.0%) | 2/2 (100.0%) | 0/1 (0.0%) | 0/2 (0.0%) | 2/2 (100.0%) | 34297.2705 | 2 | 6 | 88578/78848/1646 |
| agent_task_skill | 2/2 (100.0%) | 2/2 (100.0%) | 0/1 (0.0%) | 0/2 (0.0%) | 2/2 (100.0%) | 35918.6615 | 2 | 6 | 79611/52352/2038 |
| prepared_runner | 2/2 (100.0%) | 2/2 (100.0%) | 0/1 (0.0%) | 0/2 (0.0%) | 2/2 (100.0%) | 11540.921999999999 | 1 | 0 | 8652/0/24 |

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
| agent_direct | dev-price | completed | completed | True |  |
| agent_task_skill | dev-equality | completed | completed | True |  |
| prepared_runner | dev-equality | completed | completed | True |  |
