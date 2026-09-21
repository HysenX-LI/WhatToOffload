# Research v3: boundaries and design from raw workflows

[Completed results and limitations](RESULTS.md) · [generated formal report](results/formal-1/report.md) · [historical-case model review](results/historical-review-1/report.md)

This new version preserves all older artifacts and the v2 finding that the detailed-
spec construction pair showed no incremental Skill benefit. Two studies are separate:
semantic definition agreement and raw-workflow design. Model review is not independent
human labeling. The only actual provider in this version is ChatGPT-authenticated
Codex GPT-5.6 Sol/high; no API keys or independent paid providers are used.

Read [protocol](PROTOCOL.md), [semantic rules](SEMANTIC_RULES.md), [design rubric](RUBRIC.md)
and [split provenance](data/SPLITS.json). `EXPOSURE.jsonl`, when present, records actual
final exposure; repeating a frozen run does not make that data unseen again.

From a clean checkout, Python 3.9+ and only the standard library are needed offline:

```sh
python3 -m unittest discover -s benchmarks -t .
python3 -m benchmarks.research_v3 offline
python3 -m benchmarks.public_v1 verify --freeze benchmarks/public_v1/freeze-v1.json
python3 -m benchmarks.codex_v2 verify --freeze benchmarks/codex_v2/freeze-codex-v2.json
python3 -m benchmarks.research_v3 verify
```

Offline checks do not constitute a language-model experiment or measured model saving.
The literal gold auditor checks identities, types, arithmetic and coverage separately
from the runner. Tests also reject corrupt receipts, fabricated commitments, bad
quantities and anonymous-review identifiers. Business truth is author-labelled and
checked by blind model review; no independently recruited human annotation is claimed.

For real replication, this version requires macOS with the already logged-in CLI at
`/Applications/ChatGPT.app/Contents/Resources/codex`. The PATH installation is not used.
Do not install providers, supply API keys or change models. The invoking environment
must allow this CLI to create its own Seatbelt sandbox (a nested outer sandbox may
need an authorized launch outside that outer sandbox). Inner script/tool isolation
must remain enabled; filesystem, sibling, gold, credentials and network probes fail
closed. The model service itself uses the CLI's existing ChatGPT login.

```sh
python3 -m benchmarks.research_v3 run --stage dev --out .local/research-v3-dev-replication
# Inspect both model annotations and development acceptance before proceeding.
python3 -m benchmarks.research_v3 run --stage formal --development .local/research-v3-dev-replication --out .local/research-v3-formal-replication
python3 -m benchmarks.research_v3 report .local/research-v3-formal-replication
python3 -m benchmarks.research_v3 export .local/research-v3-formal-replication benchmarks/research_v3/results/formal-replication
cp .local/research-v3-formal-replication/calls/calls.json benchmarks/research_v3/results/formal-replication/calls/calls.json
```

The original prospective freeze command is `python3 -m benchmarks.research_v3 freeze`;
it intentionally refuses overwrite or any new freeze after final exposure. New
outcome-driven implementation work requires a new data/version directory. Do not
edit the frozen manifest to make its hashes pass. Reports regenerate only from saved
records and frozen expected denominators; no model calls. Use new output directories;
existing run directories fail rather than overwrite evidence.

Development cap 8 calls / 1200 seconds; formal cap 48 calls / 4800 seconds. Per call:
semantic/review 120 s, design/task execution 240 s, implementation/explicit debug
300 s; 40 CLI tool items. Scripts 30 s. This pair of stages caps the round at 56
calls / 6000 s, excluding offline engineering. Failure, quota and partial artifacts
are preserved. In formal runs, a local call timeout fails that phase and blocks an
incomplete build from final execution; unrelated arms continue under the same total
cap. Quota, terminal transport and global exhaustion stop the whole run. No retry loop, reset, purchase or automatic provider/model fallback.
Input/cache/output tokens and startup/context/tool/return wall time are measured;
billing and human rework remain unknown. Cached tokens are included in input.

Each workflow has two development and four withheld final cases. The one-off customer
cases are alternative situations, not repeat demand justifying automation. A design
may implement any architecture, retain Codex with aids, or simply keep the Agent.
The common result receipt and optional file-based invocation are external observation
contracts, not predesigned internal nodes. Code, design, debug notes, own dev smoke
results and code hashes are preserved; final tests never trigger repair.

The original developer sequence also contains a preserved 300 s timeout in dev-1.
The explicit second development probe subtracts that first run's 4 calls and 462
rounded-up runtime seconds from the same 8-call/1200-second allowance:

```sh
python3 -m benchmarks.research_v3 run --stage dev --continue-development --development .local/research-v3-dev-1 --out .local/research-v3-dev-2
```

This is not a retry loop. Annotation evidence is linked to the first run; its failed
construction is never relabelled successful. The partial candidate's script-only
check is separately labelled and made zero model calls. The initial un-frozen
semantic final draft, used by offline stub countertests, is retired in
`data/semantic/exposed-draft`; the replacement final changes actual judgment facts.

Original formal freeze: `209bf1d112aeabeb3231d44060172c7680ff6411195063262d292f9026a638dc`.
The public-only clean copy passed 73 tests, the v3 offline command and all three
v1/v2/v3 manifest verifications; see [clean-copy evidence](results/clean-copy-validation.json).
[First development probe](results/dev-1/report.md) and [second development probe](results/dev-2/report.md)
are separate from formal results. The second probe reused the first probe's completed
model annotations and spent only the remainder of the original development budget.

The frozen export helper omits the aggregate calls ledger, so the explicit `cp`
above includes that original measurement file unchanged. This packaging step makes
public report regeneration self-contained; no implementation, grading or scores
are altered. Per-call metrics and event audits are also preserved.

The separately registered exposed historical-case diagnostic is:

```sh
python3 -m benchmarks.research_v3.diagnostics.regression_review --formal .local/research-v3-formal-replication --out .local/research-v3-historical-review-replication
```

It runs only after formal completion and only inside the unused portion of that
formal run's original 48-call/4800-second allowance. Its two annotations are not new
final-test evidence or historical regrading. See REGRESSION_REVIEW_PROTOCOL.md and
the separate protocol/implementation manifests.

All three published development/formal reports and their SVG charts regenerated
byte-for-byte in a new public-only copy with zero model calls; see
[reproduction audit](results/report-reproduction.json). To regenerate a published
report directly:

```sh
python3 -m benchmarks.research_v3 report benchmarks/research_v3/results/formal-1
```
