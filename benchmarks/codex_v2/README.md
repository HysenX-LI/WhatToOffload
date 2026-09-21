# Public Codex benchmark v2

The active experiment uses **existing ChatGPT-authenticated Codex only**:
`gpt-5.6-sol`, reasoning `high`. No API key, independent billed model endpoint,
price table, dollar budget, paid fallback or package installation is used.
The old public_v1 API proposal and freezes are historical, unexecuted API designs;
their $60 proposal is not authorized and is not part of these commands.

The [protocol](PROTOCOL.md) separates A (prepared execution) from B (runner
construction with/without WhatToOffload). Both use the public v1 [task](../public_v1/TASK.md),
[inputs and answer tables](../public_v1/data), and independent evaluator. No private
`.local/long-benchmark` material is needed. Task decisions, approval constraints,
evidence IDs and statuses are code-owned in the prepared runner; Codex judges only
a supplied pair of documents. This study cannot establish Jev/DeepSeek/cheap-model
advantages. Billing cost is unknown even when subscription quota is used.

## Offline reproduction (Python 3.9+, standard library)

From a clean repository checkout:

```bash
python3 -m unittest discover -s benchmarks -t . -v
python3 -m benchmarks.codex_v2 run --out .local/codex-offline-dev
python3 -m benchmarks.codex_v2 report --run .local/codex-offline-dev
```

Simulation never calls Codex or model APIs. A single-input offline JSON CLI remains:

```bash
python3 -c 'import json; print(json.dumps(json.load(open("benchmarks/public_v1/data/dev/inputs.json"))[0]))' \
  | python3 -m benchmarks.public_v1.runner
```

The importable function is `benchmarks.public_v1.runner.screen(payload, judge)`.
For a single JSON stdin/stdout call with the same bounded Codex adapter, save your
input as `request.json` and run (choose a fresh log directory):

```bash
python3 -c '
import json, sys
from pathlib import Path
from benchmarks.public_v1.runner import screen
from benchmarks.codex_v2.runtime import CodexClient, preflight
from benchmarks.codex_v2.studies import CodexJudge
config = json.loads(Path("benchmarks/codex_v2/config.json").read_text())
logs = Path(".local/single-codex-call")
logs.mkdir(parents=True, exist_ok=False)
preflight(config)
client = CodexClient(config, logs)
print(json.dumps(screen(json.load(sys.stdin), CodexJudge(client))))
' < request.json
```

This entry point reads only the caller's JSON; it does not load fixtures or gold.
The study CLI below is preferred for comparisons because it additionally preserves
per-case grading, complete execution timing and the planned schedule.

## Real Codex reproduction

The provided config points to `/Applications/ChatGPT.app/Contents/Resources/codex`.
It requires an existing ChatGPT login and Codex permission-profile support. It
never uses the broken PATH installation, installs packages or changes auth/config.
The published real-run freeze uses this exact macOS CLI path and configuration.
Offline reproduction is portable. Another real execution environment needs its own
explicit environment validation and versioned protocol; it is not an identical
reproduction of this machine-specific timing study. No Docker required. Run from a normal
terminal: nesting macOS Seatbelt inside a pre-existing sandbox may be rejected.

```bash
python3 -m benchmarks.codex_v2 preflight
python3 -m benchmarks.codex_v2 matrix
python3 -m benchmarks.codex_v2 run --mode codex --study execution --split dev --limit 2 \
  --out .local/codex-dev-execution
python3 -m benchmarks.codex_v2 run --mode codex --study construction --split dev --limit 2 \
  --out .local/codex-dev-construction
# Repeat the published frozen protocol (repeatability, not newly unseen data):
python3 -m benchmarks.codex_v2 verify --freeze benchmarks/codex_v2/freeze-codex-v2.json
python3 -m benchmarks.codex_v2 run --mode codex --study both --split final \
  --freeze benchmarks/codex_v2/freeze-codex-v2.json --out .local/codex-formal
python3 -m benchmarks.codex_v2 report --run .local/codex-formal
```

Use a new output directory per run. Never replace an existing freeze.
`freeze --out NEW.json` is only for a not-yet-exposed split; the exposure ledger
rejects re-freezing this final set after it has run. The v1 provenance/freeze files
describe their original creation time; current exposure status is EXPOSURE.json. Once final
results have been inspected, an outcome-driven change requires retiring the final
split and creating a new one; rerunning unchanged code is repeatability evidence,
not another unseen test. Final status and published results are in [RESULTS.md](RESULTS.md).

Default limits per run: 60 Codex process invocations, 3600 seconds globally,
240 seconds per direct/task-Skill invocation, 120 per semantic judgment,
600 per build, 360 per candidate process, 40 tool calls per Codex invocation.
Both B groups get the same build budget. A process invocation is not an underlying
model-turn count; JSONL can report multiple tool turns within it. Internal request
count is unknown. On quota, terminal transport failure, timeout or tool/call cap, progress is saved
and the entire run stops. Codex-native bounded reconnects are recorded and may
finish within the same timeout. The harness never retries or uses a paid fallback.

Artifacts include the complete schedule, per-attempt results and grading reasons,
source hashes, candidate freezes, build investment, wall time, input/cached/output
tokens, tools and raw JSONL under `calls/`. Reports and SVG are regenerated from
records alone, without models or regrading. Unexecuted scheduled cases remain
visible separately from observed failures. Unknown token measurements and account
billing stay unknown. Candidate tools cannot read repository/gold/auth/session logs,
escape through symlinks or access the network; the host alone brokers Codex calls.

The original fixtures are authored synthetic data, not independent human labels.
One paired build does not estimate population-level Skill effects. Preparation and
required human rework remain unmeasured. Original historical reports remain intact.

To export shareable synthetic records and frozen candidates without host transcript paths:

```bash
python3 -m benchmarks.codex_v2 export --run .local/codex-formal --out .local/codex-shareable
```

The export preserves per-case outcomes, metrics, raw-event hashes and token/tool event
audits. It does not erase failed or unexecuted attempts. Full raw logs stay local.
