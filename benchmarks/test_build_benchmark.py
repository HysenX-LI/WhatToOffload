import unittest

from benchmarks.build_benchmark import summarize, validate_record


def record(run_id, arm, wall_ms, *, quality=True, budget=True, tokens=None):
    return {
        "run_id": run_id,
        "arm": arm,
        "status": "completed",
        "wall_ms": wall_ms,
        "tool_calls": 4,
        "test_commands": 1,
        "quality_pass": quality,
        "budget_compliant": budget,
        "input_tokens": tokens,
    }


class BuildBenchmarkTests(unittest.TestCase):
    def test_valid_record_and_summary_by_arm(self):
        records = [
            record("a-1", "skill", 200, tokens=1000),
            record("a-2", "skill", 180, quality=False, tokens=800),
            record("b-1", "capsule", 70, tokens=300),
        ]
        self.assertTrue(all(not validate_record(item) for item in records))
        summary = summarize(records)
        self.assertEqual(3, summary["run_count"])
        self.assertEqual(190, summary["arms"]["skill"]["median_wall_ms"])
        self.assertEqual(0.5, summary["arms"]["skill"]["quality_pass_rate"])
        self.assertEqual(70, summary["arms"]["capsule"]["p90_wall_ms"])
        self.assertEqual(300, summary["arms"]["capsule"]["median_input_tokens"])

    def test_invalid_record_reports_unknown_and_bad_fields(self):
        value = record("run", "capsule", 1)
        value["tool_calls"] = -1
        value["extra"] = "raw transcript"
        errors = validate_record(value)
        self.assertTrue(any("unknown fields" in error for error in errors))
        self.assertTrue(any("tool_calls" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
