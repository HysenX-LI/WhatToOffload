# Live benchmark

This benchmark compares the same three bounded synthetic workflows through two measured execution paths, with a third derived view:

- `codex_only`: GPT-5.6 Sol with high reasoning completes the raw task.
- `offloaded_verified`: Jev makes bounded judgments, deterministic code applies policy, DeepSeek writes the structured result, and a fresh GPT-5.6 Sol high invocation performs a thin contract check.
- `offloaded_runner_only`: the same measured offload execution with the optional Codex check removed. It is a lower-bound view, not an additional provider run, and excludes the host's small invocation/return envelope.

The fixtures cover code triage, supplied-page evidence synthesis, and business candidate screening. They do not fetch live pages or perform side effects. Each scenario and measured path runs three times; reports use medians and retain every per-run sanitized record.

## Results

![Token, latency, and cost comparison](results/comparison.svg)

- [Human-readable report](results/latest.md)
- [Machine-readable results](results/latest.json)

All 18 measured paths and all 9 derived runner-only outputs passed their scenario contracts in the recorded run. The main finding is a boundary condition: a truly bounded runner removed the per-task Sol invocation and was materially faster and cheaper, while adding a fresh Sol high verification to every result largely erased the benefit and sometimes made the path worse.

Cross-provider token totals are not treated as directly comparable because the tokenizers differ. The report therefore separates GPT-5.6 Sol main-agent tokens from Jev and DeepSeek external tokens. Codex USD values are API-price equivalents; ChatGPT plan execution consumes quota or credits rather than directly charging that amount.

Only three repetitions were requested. Sol prompt-cache hits varied across those runs, so its API-equivalent USD column is more volatile than the token and latency measurements. In particular, cost deltas for the optional verification path should be treated as directional rather than as a stable estimate.

## Run it

Real provider calls are intentionally not part of the default test suite. Set credentials only in the process environment, then opt into the live run:

```bash
export OPENROUTER_API_KEY='...'
export DEEPSEEK_API_KEY='...'
python3 -m benchmarks.benchmark --repetitions 3 --write-results
```

The benchmark uses the OpenRouter Decisions endpoint for `typesafe/jev-1.13`, DeepSeek's OpenAI-compatible Chat Completions endpoint with `deepseek-flash`, and the local Codex CLI with `gpt-5.6-sol` at high reasoning.

Raw Codex JSONL and provider diagnostics are written below `.local/benchmark-raw/`, which Git ignores. Committed results contain no credentials, authorization headers, or raw request headers.

The offline contract suite is:

```bash
python3 -m unittest benchmarks.test_benchmark -v
```

## Price snapshot

The report records a dated snapshot and source URLs for:

- [GPT-5.6 Sol API pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [Codex credit equivalents](https://learn.chatgpt.com/docs/pricing)
- [Jev 1.13 on OpenRouter](https://openrouter.ai/typesafe/jev-1.13/)
- [DeepSeek API pricing](https://api-docs.deepseek.com/quick_start/pricing/)

Re-run or update the snapshot before using these figures for a budget decision. Provider prices, aliases, and alpha endpoints can change.
