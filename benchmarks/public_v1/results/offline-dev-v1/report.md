# Public supplier screening

OFFLINE SIMULATION: validates software only. Agent arms, model quality, production latency and model costs are unmeasured.

Run: `offline-dev-v1` · split: `dev`

| Arm | Attempts | Correct | Wrong release | Review | Actual completion | Failure | Median ms | USD upper estimate |
|---|---:|---|---|---|---|---|---:|---:|
| prepared_runner | 10 | 10/10 (100.0%) | 0/5 (0.0%) | 2/11 (18.2%) | 5/10 (50.0%) | 0/10 (0.0%) | 0.054 | 0.000000 |

All numerators/denominators, citation precision, omissions and handoff counts are in report.json.
Preparation/human rework costs are unknown unless explicitly recorded in build records.

## Every attempt

| Arm | Case | Repeat | Execution | Workflow status | Grade | Reasons |
|---|---|---:|---|---|---|---|
| prepared_runner | dev-equality | 1 | completed | completed | pass | — |
| prepared_runner | dev-duplicates | 1 | completed | completed | pass | — |
| prepared_runner | dev-unclear | 1 | completed | needs_review | pass | — |
| prepared_runner | dev-price | 1 | completed | completed | pass | — |
| prepared_runner | dev-no-reference | 1 | completed | completed | pass | — |
| prepared_runner | dev-contact | 1 | completed | needs_approval | pass | — |
| prepared_runner | dev-dispute | 1 | completed | needs_review | pass | — |
| prepared_runner | dev-missing-currency | 1 | completed | needs_input | pass | — |
| prepared_runner | dev-unrelated | 1 | completed | completed | pass | — |
| prepared_runner | dev-partial | 1 | completed | needs_input | pass | — |
