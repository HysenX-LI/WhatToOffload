from __future__ import annotations

import unittest

from benchmarks.benchmark import (
    codex_cost_usd,
    deepseek_cost_usd,
    jev_questions,
    merge_usage,
    median,
    parse_json_object,
    parse_codex_jsonl,
    sanitize,
    summarize_runs,
)
from pathlib import Path
import json


class BenchmarkContractTests(unittest.TestCase):
    def test_parse_codex_jsonl_reads_final_output_and_usage(self) -> None:
        raw = "\n".join(
            [
                '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"status\\":\\"completed\\"}"}}',
                '{"type":"turn.completed","usage":{"input_tokens":1000,"cached_input_tokens":250,"output_tokens":80,"reasoning_output_tokens":20}}',
            ]
        )
        parsed = parse_codex_jsonl(raw)
        self.assertEqual(parsed["output"], {"status": "completed"})
        self.assertEqual(parsed["usage"]["input_tokens"], 1000)
        self.assertEqual(parsed["usage"]["reasoning_output_tokens"], 20)

    def test_codex_cost_does_not_double_bill_cached_or_reasoning_tokens(self) -> None:
        usage = {
            "input_tokens": 1_000_000,
            "cached_input_tokens": 250_000,
            "output_tokens": 100_000,
            "reasoning_output_tokens": 20_000,
        }
        self.assertAlmostEqual(codex_cost_usd(usage), 5.1)

    def test_deepseek_price_uses_reported_cache_split(self) -> None:
        usage = {
            "prompt_cache_hit_tokens": 100_000,
            "prompt_cache_miss_tokens": 900_000,
            "completion_tokens": 100_000,
        }
        self.assertAlmostEqual(deepseek_cost_usd(usage, peak=False), 0.1953)
        self.assertAlmostEqual(deepseek_cost_usd(usage, peak=True), 0.3906)

    def test_summary_reports_medians_for_time_tokens_cost_and_quality(self) -> None:
        runs = [
            {"wall_ms": 120, "main_agent_tokens": 10, "total_cost_usd": 0.3, "quality_pass": True},
            {"wall_ms": 80, "main_agent_tokens": 30, "total_cost_usd": 0.1, "quality_pass": False},
            {"wall_ms": 100, "main_agent_tokens": 20, "total_cost_usd": 0.2, "quality_pass": True},
        ]
        summary = summarize_runs(runs)
        self.assertEqual(summary["median_wall_ms"], 100)
        self.assertEqual(summary["median_main_agent_tokens"], 20)
        self.assertEqual(summary["median_total_cost_usd"], 0.2)
        self.assertAlmostEqual(summary["quality_pass_rate"], 2 / 3)

    def test_sanitize_redacts_secret_shaped_values(self) -> None:
        value = {"authorization": "Bearer abc", "note": "key sk-secretvalue1234567890"}
        cleaned = sanitize(value)
        self.assertEqual(cleaned["authorization"], "[REDACTED]")
        self.assertNotIn("secretvalue", cleaned["note"])

    def test_median_handles_even_and_odd_sequences(self) -> None:
        self.assertEqual(median([1, 3, 2]), 2)
        self.assertEqual(median([1, 4, 2, 3]), 2.5)

    def test_entity_specific_jev_questions_name_the_entity_in_instructions(self) -> None:
        scenarios = json.loads((Path(__file__).parent / "fixtures" / "scenarios.json").read_text())
        web = next(item for item in scenarios if item["id"] == "web-research")
        business = next(item for item in scenarios if item["id"] == "business-screening")
        for page in web["input"]["pages"]:
            self.assertIn(page["id"], jev_questions(web)["relevance__" + page["id"]]["instructions"])
        for vendor in business["input"]["vendors"]:
            self.assertIn(vendor["id"], jev_questions(business)["regulated__" + vendor["id"]]["instructions"])

    def test_parse_json_object_accepts_fenced_json_and_usage_accumulates(self) -> None:
        self.assertEqual(parse_json_object("```json\n{\"ok\": true}\n```"), {"ok": True})
        combined = merge_usage(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33},
        )
        self.assertEqual(combined["prompt_tokens"], 21)
        self.assertEqual(combined["total_tokens"], 63)


if __name__ == "__main__":
    unittest.main()
