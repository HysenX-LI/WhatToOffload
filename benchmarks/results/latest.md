# WhatToOffload live benchmark

Generated: `2026-09-19T18:07:35.154347+00:00`

Each scenario and arm ran 3 times. Medians are shown. Raw provider logs are intentionally excluded.

| Scenario | Arm | Main-agent tokens | External tokens | Wall time | Codex/Jev/DeepSeek time | Codex credits | API-equivalent cost | Quality |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| Test failure and issue triage | codex_only | 14,262 | 0 | 13.04s | 13035 ms | 1.4706 | $0.058824 | 100% |
| Test failure and issue triage | offloaded_runner_only | 0 | 1,285 | 3.33s | 0 / 779 / 1877 ms | 0.0000 | $0.000305–$0.000585 | 100% |
| Test failure and issue triage | offloaded_verified | 14,165 | 1,285 | 14.45s | 11121 / 779 / 1877 ms | 1.4503 | $0.058380–$0.058666 | 100% |
| Web evidence selection and synthesis | codex_only | 14,333 | 0 | 11.86s | 11862 ms | 0.2323 | $0.009290 | 100% |
| Web evidence selection and synthesis | offloaded_runner_only | 0 | 1,599 | 2.96s | 0 / 1663 / 1299 ms | 0.0000 | $0.000198–$0.000353 | 100% |
| Web evidence selection and synthesis | offloaded_verified | 14,125 | 1,599 | 14.17s | 11438 / 1663 / 1299 ms | 0.2079 | $0.008479–$0.008600 | 100% |
| Business intake and vendor screening | codex_only | 14,268 | 0 | 8.56s | 8564 ms | 0.2226 | $0.008902 | 100% |
| Business intake and vendor screening | offloaded_runner_only | 0 | 1,872 | 4.07s | 0 / 1456 / 2611 ms | 0.0000 | $0.000443–$0.000849 | 100% |
| Business intake and vendor screening | offloaded_verified | 14,132 | 1,872 | 15.20s | 10280 / 1456 / 2611 ms | 1.4432 | $0.058169–$0.058452 | 100% |

## Relative change

| Scenario | Main-agent token reduction | End-to-end latency reduction | API-equivalent cost reduction |
| --- | ---: | ---: | ---: |
| Test failure and issue triage — Runner only | +100.0% | +74.4% | +99.5% |
| Test failure and issue triage — With Codex verification | +0.7% | -10.9% | +0.8% |
| Web evidence selection and synthesis — Runner only | +100.0% | +75.0% | +97.9% |
| Web evidence selection and synthesis — With Codex verification | +1.5% | -19.5% | +8.7% |
| Business intake and vendor screening — Runner only | +100.0% | +52.5% | +95.0% |
| Business intake and vendor screening — With Codex verification | +1.0% | -77.5% | -553.4% |

## Interpretation notes

- Main-agent tokens compare GPT-5.6 Sol usage within the same tokenizer. External-token totals are shown separately because Jev and DeepSeek use different tokenizers.
- Codex cost is an API-price equivalent; a ChatGPT plan consumes quota/credits rather than charging that USD amount per run.
- With only three repetitions, Sol cache hits varied between runs and made API-equivalent cost volatile. Treat verified-path cost deltas as directional; the token and latency columns expose the underlying work more directly.
- DeepSeek is shown as an off-peak-to-peak range. Jev uses the OpenRouter Jev 1.13 input price recorded for this run.
- Runner-only is a measured lower-bound view derived by removing the optional Codex verification from the same offload run. It excludes the host's small invocation/return envelope.
- Wall time is sequential end-to-end latency. The verified offload component order is Codex thin check / Jev / DeepSeek.
- The fixtures are synthetic and bounded. This measures operating cost and latency, not the one-time engineering cost of building the runner.

## Price snapshot

- GPT-5.6 Sol: $4/M uncached input, $0.40/M cached input, $20/M output.
- Jev 1.13 on OpenRouter: $0.042/M input, $0 output.
- DeepSeek Flash: off-peak $0.003/M cache-hit input, $0.15/M cache-miss input, $0.60/M output; peak prices are double.
