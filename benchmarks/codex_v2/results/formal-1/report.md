# Codex supplier screening v2

CODEX MEASURED: ChatGPT authentication; GPT-5.6 Sol / high. Account billing cost unknown.

Run: `codex-v2-formal-1`; split: `final`; stop: `None`.

One paired repetition is descriptive; no Jev/DeepSeek/cheap-model or population claim.

| Arm | Executed/planned | Correct/planned | Wrong release | Review | Actual completion | Median ms | Codex calls | Tools | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---:|---|
| agent_direct | 8/8 (100.0%) | 8/8 (100.0%) | 0/6 (0.0%) | 3/12 (25.0%) | 2/8 (25.0%) | 30549.241 | 8 | 24 | 268541/198016/7158 |
| agent_task_skill | 8/8 (100.0%) | 8/8 (100.0%) | 0/6 (0.0%) | 3/12 (25.0%) | 2/8 (25.0%) | 40340.865999999995 | 8 | 24 | 345302/279552/9692 |
| build_with_skill | 8/8 (100.0%) | 7/8 (87.5%) | 0/6 (0.0%) | 4/12 (33.3%) | 2/8 (25.0%) | 9091.5355 | 8 | 0 | 69394/33280/186 |
| build_without_skill | 8/8 (100.0%) | 7/8 (87.5%) | 0/6 (0.0%) | 4/12 (33.3%) | 2/8 (25.0%) | 9228.5965 | 8 | 0 | 69407/39936/186 |
| prepared_runner | 8/8 (100.0%) | 7/8 (87.5%) | 0/6 (0.0%) | 4/12 (33.3%) | 2/8 (25.0%) | 8859.2755 | 8 | 0 | 69393/46592/186 |

Cached input is included in input tokens. Startup/context/return time included; grading excluded.
Additional metrics with numerators, denominators and token completeness are in report.json.
Prepared runner/task Skill preparation and required human rework are unknown. Billing is unknown, not zero.

## Construction investment (separate from execution)

| Arm | Status | Syntax | Runnable | Correct | Boundary decisions | Build ms | Calls | Input/cache/output tokens |
|---|---|---|---|---|---|---:|---:|---|
| build_with_skill | completed | True | 8/8 | 7/8 | 3/3 | 299038.194 | 1 | 400972/366080/14846 |
| build_without_skill | completed | True | 8/8 | 7/8 | 3/3 | 297613.58 | 1 | 325686/277760/14530 |

## Every scheduled attempt

| Arm | Case | Execution | Status | Accepted | Failure reasons |
|---|---|---|---|---|---|
| build_without_skill | final-duplicate-identities | completed | needs_review | True |  |
| build_without_skill | final-contact-partial-eligibility | completed | needs_review | False | request mismatch: approval_required; request mismatch: status; row mismatch: e |
| build_without_skill | final-empty-pack | completed | needs_input | True |  |
| prepared_runner | final-unclear-with-noise | completed | needs_review | True |  |
| build_without_skill | final-unclear-with-noise | completed | needs_review | True |  |
| agent_direct | final-missing-precedence | completed | needs_input | True |  |
| prepared_runner | final-duplicate-identities | completed | needs_review | True |  |
| build_with_skill | final-contact-partial-eligibility | completed | needs_review | False | request mismatch: approval_required; request mismatch: status; row mismatch: e |
| agent_direct | final-empty-pack | completed | needs_input | True |  |
| agent_task_skill | final-contact-partial-eligibility | completed | needs_approval | True |  |
| agent_task_skill | final-disputed-scope | completed | needs_review | True |  |
| agent_task_skill | final-duplicate-identities | completed | needs_review | True |  |
| prepared_runner | final-disputed-scope | completed | needs_review | True |  |
| build_with_skill | final-revision-and-ranking | completed | completed | True |  |
| prepared_runner | final-policy-change | completed | completed | True |  |
| build_with_skill | final-duplicate-identities | completed | needs_review | True |  |
| build_without_skill | final-missing-precedence | completed | needs_input | True |  |
| build_without_skill | final-revision-and-ranking | completed | completed | True |  |
| agent_direct | final-unclear-with-noise | completed | needs_review | True |  |
| agent_task_skill | final-unclear-with-noise | completed | needs_review | True |  |
| build_with_skill | final-empty-pack | completed | needs_input | True |  |
| agent_direct | final-contact-partial-eligibility | completed | needs_approval | True |  |
| agent_direct | final-disputed-scope | completed | needs_review | True |  |
| agent_direct | final-duplicate-identities | completed | needs_review | True |  |
| agent_task_skill | final-policy-change | completed | completed | True |  |
| build_with_skill | final-missing-precedence | completed | needs_input | True |  |
| prepared_runner | final-revision-and-ranking | completed | completed | True |  |
| agent_task_skill | final-missing-precedence | completed | needs_input | True |  |
| prepared_runner | final-empty-pack | completed | needs_input | True |  |
| agent_direct | final-policy-change | completed | completed | True |  |
| agent_direct | final-revision-and-ranking | completed | completed | True |  |
| build_with_skill | final-disputed-scope | completed | needs_review | True |  |
| build_with_skill | final-policy-change | completed | completed | True |  |
| agent_task_skill | final-empty-pack | completed | needs_input | True |  |
| prepared_runner | final-contact-partial-eligibility | completed | needs_review | False | request mismatch: approval_required; request mismatch: status; row mismatch: e |
| build_without_skill | final-disputed-scope | completed | needs_review | True |  |
| build_without_skill | final-policy-change | completed | completed | True |  |
| agent_task_skill | final-revision-and-ranking | completed | completed | True |  |
| prepared_runner | final-missing-precedence | completed | needs_input | True |  |
| build_with_skill | final-unclear-with-noise | completed | needs_review | True |  |
