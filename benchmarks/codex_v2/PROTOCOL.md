# Codex supplier-screening protocol v2

This amendment replaces the unexecuted independent-API proposal in public_v1.
The v1 freezes and simulation results remain historical, immutable artifacts.
Acceptance, public synthetic fixtures and independent gold/evaluator remain v1.
No final executor has run at amendment creation. EXPOSURE.json records subsequent
exposure and prevents creating a new supposedly-unseen freeze after a final run. No calibration or threshold tuning.

## Runtime and isolation

All model work uses fresh `codex exec --ephemeral --ignore-user-config` processes,
ChatGPT authentication only, `gpt-5.6-sol`, reasoning `high`. Never resume/fork or
pass evaluator conversation. Never call an independently billed model API, require
API keys, buy credits or fall back to another provider/model. Credentials are not
passed to model tools. Host skills, plugins, apps, memory, hooks, web and subagents
are disabled; treatment documents are supplied explicitly in the temporary folder.
Local tools have a minimal-runtime plus single-workspace permission profile, no
network and no approval escalation. Repository, gold, scorer, other workspaces,
session logs and auth files are inaccessible to tool commands. Generated scripts
execute as subprocesses under the same filesystem/network policy, never imported
by the evaluator. Isolation probes must succeed before any model call.

## A: prepared execution

`agent_direct`, `agent_task_skill`, `prepared_runner` receive identical inputs and
acceptance. Direct and Skill agents may use shell/Python scripts; only the treatment
receives TASK_SKILL.md. Prepared code owns protected business fields and calls Codex
for bounded profile/reference judgments. Codex receives only those source records,
domain and semantic contract. No Jev, DeepSeek or cheap-model claim follows.

## B: construction

`build_without_skill` and `build_with_skill` each receive the same TASK.md, unlabelled
development inputs, helpers, semantic bridge, workflow boundary probes, tool access,
model and 600-second / 40-tool-call budget. Only the latter receives WhatToOffload
SKILL.md and its referenced resources. Each gets one fresh Codex invocation; no
human repair or continuation. Hash candidate.py before final input exposure. Restore
neutral helpers when evaluating candidates. Both candidates use the same Codex
semantic adapter as the prepared runner. Report construction separately from later
execution, including workflow offload decisions, syntax, runnability and acceptance.
No-Skill construction is not direct task execution. Retain failed builds and attempts.

## Measurement and stopping

Wall clock includes temporary workspace setup, Codex startup, context upload, all
tools/retries inside that invocation, result return and parsing; excludes grading.
Preparation cost of the prebuilt runner/task Skill remains unknown. Build investment
is measured separately; required human rework remains unknown (no repairs attempted).
Record Codex process invocations, JSONL-reported input/cached/output tokens, tool
events, raw events, errors, timeout, return code and result for every attempt.
Tool counts and the tool-event watchdog count unique CLI-exposed tool item IDs;
unreported internal invocations are unknown, not inferred from text. The builder
prompt also requests at most 40 tool calls, and wall-clock limits are enforced.
Cached tokens are a subset of input, never added again. Missing usage is null; show
known subtotals and completeness. A Codex invocation can include several underlying
model turns: internal model-request count is unknown, not the process count.
Subscription/account billing is unknown, never zero; no dollar limits or prices.

The checked-in config limits an entire run to 60 Codex invocations / 3600 seconds;
each agent 240 s, semantic call 120 s, build 600 s, candidate 360 s and each Codex
invocation 40 tool calls. Reserve a process slot before launch, including failures.
Stop the whole run on quota/rate exhaustion, process/tool/time limits, terminal
transport failure, or incomplete return; save remaining planned attempts as not_executed. Never perform harness-level retries or change model/provider. Codex-native bounded
reconnections may finish inside the original call timeout; each reconnect event is
retained and counted. Unbounded connection retries are disabled. Reported usage
may exclude failed internal transmissions; the underlying request/billing total
remains unknown. Quality failures with a returned result remain in the
dataset and do not change prompts, implementation, gold or scoring.

Quality metrics retain v1 numerators/denominators and add execution coverage.
Scheduled-but-unexecuted cases count against scheduled correctness, are separately
identified, and are not mislabelled as observed execution failures. Also show quality
among observed attempts, with the coverage next to it. All-review cannot win.

## Sequence and inference

Run offline regression and isolation probes first, then the first two development
cases through all three execution arms, plus one build per construction arm and
candidate development checks. Fix only using development evidence if needed. Freeze
implementation, prompts, config, scoring and both data splits in a new manifest.
Then run one paired construction repetition and one randomized execution/candidate
repetition over all final cases. Formal candidates are rebuilt in fresh contexts;
development candidates are not reused. Do not tune after inspecting final outcomes.
One paired build and eight public synthetic cases support descriptive observations,
not a causal population estimate, significance claim or blind external benchmark.
The same author implemented and authored gold; prospective isolation is not external
independent adjudication. Additional outcome-driven work retires this final set.

References for runtime configuration: [permissions](https://learn.chatgpt.com/docs/permissions)
and [authentication settings](https://learn.chatgpt.com/docs/config-file/config-reference).

This single pair builds without Skill first, then with Skill. Provider caching,
server load and this fixed build order are uncontrolled; reported cache tokens do
not remove that confounding. Execution/candidate attempts are seed-shuffled and
run sequentially. Development and final runs do not overlap.

Semantic bridge interface clarification before final freeze: a candidate may send
the unchanged source dictionaries or projections containing their original id and
text. The broker matches both to the same vendor and forwards original input
records to Codex. Changed/foreign facts are rejected; no gold is used by the broker.
