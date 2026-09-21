# Codex supplier screening v2

CODEX MEASURED: ChatGPT authentication; GPT-5.6 Sol / high. Account billing cost unknown.

Run: `codex-v2-dev-execution-2`; split: `dev`; stop: `None`.

One paired repetition is descriptive; no Jev/DeepSeek/cheap-model or population claim.

| Arm | Executed/planned | Correct/planned | Wrong release | Review | Actual completion | Median ms | Codex calls | Tools | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---:|---|
| agent_direct | 2/2 (100.0%) | 2/2 (100.0%) | 0/1 (0.0%) | 0/2 (0.0%) | 2/2 (100.0%) | 72014.50649999999 | 2 | 7 | 174920/125440/4652 |
| agent_task_skill | 2/2 (100.0%) | 2/2 (100.0%) | 0/1 (0.0%) | 0/2 (0.0%) | 2/2 (100.0%) | 59407.932 | 2 | 6 | 136036/99840/3119 |
| prepared_runner | 2/2 (100.0%) | 1/2 (50.0%) | unknown | 0/2 (0.0%) | 1/2 (50.0%) | 4910.2795 | 1 | 0 | 8653/0/24 |

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
| prepared_runner | dev-equality | failed | failed | False | request mismatch: shortlist; request mismatch: status; row mismatch: a; executor_reported_failure |
