# Public supplier-screening benchmark v1

A minimal public experiment with **one** short-lived workflow. Python 3.9+ and the
standard library are sufficient for offline reproduction. No `.local/long-benchmark/`
files, private material, API key, Docker, third-party Python package or network are
needed for the offline checks.

Current evidence: [offline development report](results/offline-dev-v1/report.md).
It tests software with a deliberately limited phrase fake. It does **not** establish
real model quality, production speed/cost savings, or the incremental value of the
WhatToOffload Skill. The final set has not been executed at delivery.

## What is included

- [Predeclared protocol and metric definitions](PROTOCOL.md).
- [Executor-facing task/contract](TASK.md), fixed [development inputs](data/dev/inputs.json)
  and separately authored [final inputs](data/final/inputs.json).
- Independent literal answer tables with case rationales under each split's
  `gold.json`. [Provenance and split policy](data/SPLITS.json).
- `runner.py`: importable `screen(payload, judge)` and JSON CLI. Deterministic
  policies own protected fields; semantic adapters judge only a document pair.
- `evaluate.py`: table comparison and separate sanity checks of gold identities,
  arithmetic and coverage. No import of runner policy code. Structural validators
  are shared; decision functions are not. This is not independent human annotation.
- `experiments.py`: three prepared-execution arms and two distinct construction
  arms, with isolated contexts and identical model/tools/budgets within a comparison.
- `sandbox.py`: model-authored Python can run only inside an isolated Docker
  container. Repository/gold/tests/host credentials are never mounted.
- `report.py`: all counts, ratios and SVG bars come from preserved attempt records.
- Three boundary probes, including two workflows that should remain with an agent.

## Reproduce from a clean checkout

Run from the repository root; use a new output directory for each run:

```bash
python3 -m unittest discover -s benchmarks -t . -v
python3 -m benchmarks.public_v1 run --split dev --out .local/public-dev-reproduction
python3 -m benchmarks.public_v1 report --run .local/public-dev-reproduction
python3 -m benchmarks.public_v1 verify --freeze benchmarks/public_v1/freeze-v1.json
```

Outputs: `plan.json`, append-only `attempts.jsonl`, `metadata.json`, `report.json`,
`report.md`, `comparison.svg`, and separate construction reports. A nonzero exit
means at least one scheduled attempt failed acceptance; all attempts are retained.
An interrupted attempt remains visible as failure with unknown measurements.
Reporting reads saved records and does not rerun providers or regrade with new gold.
Existing output directories are rejected, including the archived result directory.

Run one input through the JSON CLI:

```bash
python3 -c 'import json; print(json.dumps(json.load(open("benchmarks/public_v1/data/dev/inputs.json"))[0]))' \
  | python3 -m benchmarks.public_v1.runner
```

Or import without loading any dataset or answer file:

```python
from benchmarks.public_v1.runner import screen
from benchmarks.public_v1.providers import OfflineJudge

result = screen(payload, OfflineJudge())
```

The phrase fake recognizes only a few explicit patterns, has no gold lookup, and
cannot justify claims about language understanding. Provider failure and malicious
structured outputs are tested through injected fakes in the unit suite.

## Data and final-test discipline

Development: 10 cases / 11 vendor records. Final: 8 cases / 12 records. Cases change
revision precedence, missing-data versus disqualification priority, semantic
contradiction versus unknown evidence, source identity, required regions, reference
requirements, ranking ties and approval boundaries. No confidence threshold is
tuned, so no artificial calibration split is provided.

The same author wrote the implementation and synthetic labels: this is a
prospective local holdout for the executors, not an independently blind study. The
final files are publicly inspectable by humans but never exposed to construction
agents. They have had schema/arithmetic audits only, not executor evaluation.
CI runs the development set, not the final set. A pre-authoring implementation
snapshot is retained; the authoritative final freeze also records the pre-formal
summary-contract amendment described in `data/SPLITS.json`.

`freeze-v1.json` hashes runtime, prompts, grading rules, protocol, split files and
the actual WhatToOffload Skill/resources used as treatment. Final execution rejects
changed hashes. Each constructed candidate is hashed before seeing any final case.
Do not replace a used freeze to make changes pass: if final outcomes inform a fix,
retire the entire final split into development, author a new final version and
create a new freeze. Repeated runs of a frozen candidate measure repeatability,
not new independent inputs.

## Live pilot: explicit authorization still required

No paid calls were made during implementation. The proposed pilot uses the same
`gpt-5.6-sol`, high reasoning, standard service tier in all arms and in the semantic
adapter. This deliberately tests architecture without confounding it with cheaper
models. There is no Jev-specific contribution claim or extra ablation matrix.

The configured model supports Chat Completions, function calling and structured
outputs according to [official model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-sol).
The adapter uses `max_completion_tokens` to bound visible plus reasoning output and
requests the standard service tier; see the [API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
No service compatibility probe has been executed with this account.

Generate the reviewable call matrix without credentials or network:

```bash
python3 -m benchmarks.public_v1 matrix --split final
```

For one repetition:

| Study | Prepared work | Final executions | Maximum HTTP calls |
|---|---|---:|---:|
| A: direct agent / task-Skill agent / prepared runner | Existing runner; setup cost unknown | 24 | 108 |
| B: build without / with WhatToOffload | 2 independent builds, max 10 model turns each | 16 | 44 |
| Combined | 2 builds | 40 | 152 |

These numbers are a readable snapshot of `matrix`; recalculate after any config or
data change. Every arm has the same final input and acceptance rules. Both A agent
arms can execute scripts, with a maximum 6 model turns per case. Both B builders
receive the same task, development inputs without labels, neutral helpers and
workflow probes; the Skill and its design resources are the only treatment.
Construction outputs are not repaired during evaluation. Construction reports
separate build cost/time/usage, syntax validity, candidate runnability/acceptance,
boundary choices and unknown human rework. A direct-task baseline is never used as
the no-Skill construction baseline.

The example config reserves at most **$60** total and permits at most **160** HTTP
requests. It reserves **$0.38096** before each request and never refunds a failed
request's reservation. The 152-call matrix has a conservative reservation ceiling
of **$57.90592**, not an expected bill. The dated upper input rate is $5/M (covering
Sol cache writes), output $20/M, with a 48,000-byte input cap plus 8,192-token protocol
allowance and 5,000 total completion-token cap. This stays below long-context pricing
thresholds. Costs in reports are upper-rate estimates from measured usage, not
invoices; missing usage remains unknown. Verify rates again if running after the
snapshot date (2026-09-20), or when changing provider/model. Client reservations
depend on the provider honoring the selected model, tier and token limits.

After authorization, prepare Docker and a local Python image separately, then:

```bash
mkdir -p .local
cp benchmarks/public_v1/live-config.example.json .local/public-live-config.json
# Set OPENAI_API_KEY in the process environment through your normal secret handling.
# Ensure Docker is running and python:3.11-slim is already available locally.
python3 -m benchmarks.public_v1 run --live --study both --split final \
  --config .local/public-live-config.json \
  --freeze benchmarks/public_v1/freeze-v1.json \
  --out .local/public-live-v1
```

The container image ID, chosen model, config, runtime hashes, per-call safe usage,
errors and per-case results are recorded. Calls are sequential; attempt order is
seeded and shuffled. Docker image pulls are disabled during experiments. No Docker
means agent/build experiments stop before provider calls. Model-produced scripts
never run on the host. The Docker-backed path has not been integration-tested on
this development machine, which does not have Docker.

For a separately authorized single runner call, use `runner --live --config ...`.
The complete studies use the harness above because it preserves failures and usage.

## Interpretation boundaries

A can establish prepared repeat-execution behavior on this task after live calls;
it cannot establish net lifetime savings without setup and maintenance costs.
B can estimate the incremental effect of **offering** the Skill during construction
after live builds; it does not guarantee the agent actually followed every instruction.
One build per arm and eight cases are a pilot, not a statistical generalization
claim. Human annotation independence, human rework and provider cache control remain
limitations. The prototype does not evaluate open-ended prose quality: its summary
is a fixed factual receipt and its authoritative output is the structured table.

Historical microbenchmark repairs are documented in the parent benchmark README.
The absent private long-task runner has not been inspected or attributed these bugs.
