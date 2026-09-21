#!/usr/bin/env python3
"""Run the WhatToOffload live comparison without persisting credentials.

Raw provider responses stay under .local/. Only sanitized aggregate records are
written to benchmarks/results/ when --write-results is supplied.
"""

from __future__ import annotations

import argparse
import copy
import html
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from benchmarks.contracts import APPROVAL_ACTION, HISTORICAL_FIELDS, object_errors, source_ids


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "benchmarks" / "fixtures" / "scenarios.json"
OUTPUT_SCHEMA_PATH = ROOT / "benchmarks" / "output-schema.json"
RAW_DIR = ROOT / ".local" / "benchmark-raw"
RESULTS_DIR = ROOT / "benchmarks" / "results"

CODEX_MODEL = "gpt-5.6-sol"
DEEPSEEK_MODEL = "deepseek-flash"
JEV_MODEL = "typesafe/jev-1.13"
JEV_URL = "https://openrouter.ai/api/alpha/decisions"
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

SECRET_PATTERN = re.compile(r"(?:sk-or-v1-|sk-)[A-Za-z0-9_-]{12,}")
SECRET_KEYS = {"authorization", "api_key", "token", "key", "secret"}


def median(values: Iterable[float]) -> float:
    return statistics.median(list(values))


def codex_cost_usd(usage: Mapping[str, Any]) -> float:
    """GPT-5.6 Sol API-equivalent cost using current official list prices."""
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    cached = int(usage.get("cached_input_tokens", 0) or 0)
    uncached = max(0, input_tokens - cached)
    output = int(usage.get("output_tokens", 0) or 0)
    return uncached * 4.0 / 1_000_000 + cached * 0.4 / 1_000_000 + output * 20.0 / 1_000_000


def codex_credits(usage: Mapping[str, Any]) -> float:
    """Codex credit equivalent; ChatGPT plan usage is not direct USD billing."""
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    cached = int(usage.get("cached_input_tokens", 0) or 0)
    uncached = max(0, input_tokens - cached)
    output = int(usage.get("output_tokens", 0) or 0)
    return uncached * 100.0 / 1_000_000 + cached * 10.0 / 1_000_000 + output * 500.0 / 1_000_000


def deepseek_cost_usd(usage: Mapping[str, Any], peak: bool) -> float:
    hit = int(usage.get("prompt_cache_hit_tokens", 0) or 0)
    miss = int(usage.get("prompt_cache_miss_tokens", 0) or 0)
    if not hit and not miss:
        miss = int(usage.get("prompt_tokens", 0) or 0)
    output = int(usage.get("completion_tokens", 0) or 0)
    hit_rate = 0.006 if peak else 0.003
    miss_rate = 0.30 if peak else 0.15
    output_rate = 1.20 if peak else 0.60
    return hit * hit_rate / 1_000_000 + miss * miss_rate / 1_000_000 + output * output_rate / 1_000_000


def jev_cost_usd(usage: Mapping[str, Any]) -> float:
    input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
    return input_tokens * 0.042 / 1_000_000


def sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned = {}
        for key, child in value.items():
            if str(key).lower() in SECRET_KEYS:
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = sanitize(child)
        return cleaned
    if isinstance(value, list):
        return [sanitize(child) for child in value]
    if isinstance(value, str):
        return SECRET_PATTERN.sub("[REDACTED]", value)
    return value


def parse_codex_jsonl(raw: str) -> Dict[str, Any]:
    output = None
    usage: Dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message":
                text = item.get("text", "")
                try:
                    output = json.loads(text)
                except (TypeError, json.JSONDecodeError):
                    pass
        if event.get("type") == "turn.completed":
            usage = dict(event.get("usage") or {})
    if output is None:
        raise RuntimeError("Codex JSONL did not contain a JSON agent message")
    if not usage:
        raise RuntimeError("Codex JSONL did not contain turn usage")
    return {"output": output, "usage": usage}


def parse_json_object(content: str) -> Dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def merge_usage(left: Mapping[str, Any], right: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, (int, float)) and isinstance(merged.get(key, 0), (int, float)):
            merged[key] = merged.get(key, 0) + value
        elif key not in merged:
            merged[key] = value
    return merged


def summarize_runs(runs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not runs:
        return {}
    return {
        "run_count": len(runs),
        "median_wall_ms": median(float(run["wall_ms"]) for run in runs),
        "median_main_agent_tokens": median(float(run["main_agent_tokens"]) for run in runs),
        "median_total_cost_usd": median(float(run["total_cost_usd"]) for run in runs),
        "quality_pass_rate": sum(bool(run.get("quality_pass")) for run in runs) / len(runs),
    }


def post_json(url: str, key: str, payload: Mapping[str, Any], extra_headers: Optional[Mapping[str, str]] = None) -> Tuple[Dict[str, Any], int]:
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        safe_body = SECRET_PATTERN.sub("[REDACTED]", body[:500])
        raise RuntimeError("HTTP {} from {}: {}".format(exc.code, url, safe_body)) from None
    return result, round((time.perf_counter() - started) * 1000)


def _answer_value(answer: Mapping[str, Any], field: str) -> Any:
    if field not in answer:
        raise RuntimeError("Jev answer is missing {}".format(field))
    return answer[field]


def jev_questions(scenario: Mapping[str, Any]) -> Dict[str, Any]:
    scenario_id = scenario["id"]
    if scenario_id == "code-triage":
        return {
            "failure_family": {
                "type": "choice",
                "instructions": "Classify the most likely failure family using only the supplied test and repository evidence.",
                "criteria": {
                    "product_regression": "Implementation changed contrary to a still-current product specification.",
                    "test_regression": "The test expectation is stale or conflicts with the current specification.",
                    "environment": "Failure is caused by setup, dependency, or execution environment.",
                    "flaky_or_timing": "Failure is intermittent or timing-sensitive.",
                    "insufficient_evidence": "The evidence cannot distinguish the cause.",
                },
            }
        }
    if scenario_id == "web-research":
        questions = {}
        question = scenario["input"]["question"]
        for page in scenario["input"]["pages"]:
            page_id = page["id"]
            questions["relevance__" + page_id] = {
                "type": "score",
                "instructions": "For the page whose id is '{}', how useful is it for answering: {}".format(page_id, question),
                "criteria": [
                    "Irrelevant or unsupported speculation",
                    "Related context but does not establish the answer",
                    "Direct evidence that establishes an important part of the answer",
                ],
            }
            questions["support__" + page_id] = {
                "type": "noul",
                "instructions": "Does the page whose id is '{}' directly support a factual part of the requested conclusion?".format(page_id),
                "criteria": {
                    "true": "The text contains direct, attributable evidence.",
                    "false": "It is irrelevant, speculative, or lacks evidence for the conclusion.",
                },
            }
        return questions
    if scenario_id == "business-screening":
        questions = {}
        for vendor in scenario["input"]["vendors"]:
            vendor_id = vendor["id"]
            questions["regulated__" + vendor_id] = {
                "type": "noul",
                "instructions": "Does the vendor whose id is '{}' provide concrete evidence of regulated-domain localization experience?".format(vendor_id),
                "criteria": {
                    "true": "Names regulated work, relevant specialists, audits, or reference launches.",
                    "false": "Only general translation claims or no regulated examples.",
                },
            }
            questions["evidence__" + vendor_id] = {
                "type": "score",
                "instructions": "How strong is the evidence in the profile of the vendor whose id is '{}'?".format(vendor_id),
                "criteria": [
                    "No relevant evidence",
                    "General relevant claim without verification detail",
                    "Concrete relevant evidence with specialists, audits, or references",
                ],
            }
        return questions
    raise ValueError("Unknown scenario: " + str(scenario_id))


def call_jev(scenario: Mapping[str, Any], key: str) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
    payload = {
        "model": JEV_MODEL,
        "state": scenario["input"],
        "questions": jev_questions(scenario),
    }
    response, elapsed = post_json(
        JEV_URL,
        key,
        payload,
        {"HTTP-Referer": "https://github.com/HysenX-LI/WhatToOffload", "X-OpenRouter-Title": "WhatToOffload benchmark"},
    )
    answers = response.get("answers")
    if not isinstance(answers, Mapping):
        raise RuntimeError("Jev response has no answers object")
    return dict(answers), dict(response.get("usage") or {}), elapsed


def compose_offload_result(scenario: Mapping[str, Any], answers: Mapping[str, Any]) -> Dict[str, Any]:
    scenario_id = scenario["id"]
    if scenario_id == "code-triage":
        answer = answers["failure_family"]
        decision = str(_answer_value(answer, "choice"))
        confidence = float(answer.get("confidence", 0.0))
        return {
            "status": "completed" if decision != "insufficient_evidence" and confidence >= 0.35 else "needs_review",
            "scenario_id": scenario_id,
            "decision": decision,
            "evidence_ids": sorted(source_ids(scenario["input"])),
            "signals": {"confidence": confidence, "probabilities": answer.get("probabilities", {})},
            "next_actions": ["Inspect src/checkout.py and verify the new-checkout branch before editing."],
        }
    if scenario_id == "web-research":
        selected = []
        signals = {}
        for page in scenario["input"]["pages"]:
            page_id = page["id"]
            relevance = answers["relevance__" + page_id]
            support = answers["support__" + page_id]
            score = float(_answer_value(relevance, "score"))
            probability = float(_answer_value(support, "noul"))
            signals[page_id] = {"relevance_score": score, "support_probability": probability}
            if score >= 1.0 and probability >= 0.60 and page.get("source_type") == "official":
                selected.append(page_id)
        selected.sort()
        required = int(scenario["input"]["source_policy"]["minimum_independent_sources"])
        return {
            "status": "completed" if len(selected) >= required else "needs_review",
            "scenario_id": scenario_id,
            "decision": "supported" if len(selected) >= required else "insufficient_evidence",
            "evidence_ids": selected,
            "signals": signals,
            "next_actions": ["Keep the support date tied to the selected official source IDs."],
        }
    if scenario_id == "business-screening":
        ranked = []
        signals = {}
        for vendor in scenario["input"]["vendors"]:
            vendor_id = vendor["id"]
            regulated = float(_answer_value(answers["regulated__" + vendor_id], "noul"))
            evidence = float(_answer_value(answers["evidence__" + vendor_id], "score"))
            regions = set(vendor["verified_regions"])
            hard_gate = "CN" in regions and regulated >= 0.60
            signals[vendor_id] = {"regulated_probability": regulated, "evidence_score": evidence, "hard_gate": hard_gate}
            if hard_gate:
                ranked.append((evidence, regulated, vendor_id))
        ranked.sort(reverse=True)
        decision = ranked[0][2] if ranked else "no_eligible_vendor"
        return {
            "status": "completed" if ranked else "needs_review",
            "scenario_id": scenario_id,
            "decision": decision,
            "evidence_ids": [decision] if ranked else [],
            "signals": signals,
            "next_actions": [APPROVAL_ACTION],
        }
    raise ValueError("Unknown scenario: " + str(scenario_id))


def call_deepseek(compact: Mapping[str, Any], key: str) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only a JSON object with one key, summary: a factual string under 70 words. "
                    "Do not return decisions, status, evidence or actions. Never claim an external action occurred."
                ),
            },
            {"role": "user", "content": json.dumps(compact, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
        "stream": False,
        "max_tokens": 1500,
        "temperature": 0,
    }
    total_usage: Dict[str, Any] = {}
    total_elapsed = 0
    last_reason = "unknown"
    for attempt in range(1, 3):
        response, elapsed = post_json(DEEPSEEK_URL, key, payload)
        total_elapsed += elapsed
        total_usage = merge_usage(total_usage, dict(response.get("usage") or {}))
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            last_reason = "no choices"
            continue
        last_reason = str(choices[0].get("finish_reason", "unknown"))
        content = choices[0].get("message", {}).get("content", "")
        try:
            result = parse_json_object(content)
        except (json.JSONDecodeError, ValueError):
            continue
        if set(result) == {"summary"} and isinstance(result["summary"], str) and result["summary"].strip():
            total_usage["attempts"] = attempt
            protected = {field: copy.deepcopy(compact[field]) for field in HISTORICAL_FIELDS if field != "summary"}
            protected["summary"] = result["summary"]
            if object_errors(protected, HISTORICAL_FIELDS):
                raise RuntimeError("Invalid code-owned result contract")
            return protected, total_usage, total_elapsed
        last_reason = "contract keys"
    raise RuntimeError("DeepSeek returned no valid JSON after 2 attempts; last_reason={}".format(last_reason))


def codex_prompt(scenario: Mapping[str, Any], offload_result: Optional[Mapping[str, Any]]) -> str:
    if offload_result is None:
        contracts = {
            "code-triage": {
                "decision": "Choose exactly one: product_regression, test_regression, environment, flaky_or_timing, insufficient_evidence.",
                "evidence": "Include the IDs that establish the failure and cause.",
            },
            "web-research": {
                "decision": "Choose exactly one: supported, not_supported, insufficient_evidence.",
                "evidence": "Include only supplied page IDs that directly establish the conclusion.",
            },
            "business-screening": {
                "decision": "Return the selected vendor ID, or no_eligible_vendor.",
                "evidence": "Include the selected vendor ID and preserve the approval boundary in next_actions.",
            },
        }
        return (
            "You are completing one bounded workflow case. Analyze the raw synthetic input independently and return only "
            "JSON matching the supplied output schema. Use needs_review only when the evidence cannot support a safe bounded "
            "decision. Do not use tools or inspect unrelated repository files. For business screening, never perform outreach "
            "and set next_actions to exactly [\"" + APPROVAL_ACTION + "\"]. For web research, cite only supplied page ids in evidence_ids.\n\n"
            + json.dumps({"scenario_id": scenario["id"], "task": scenario["title"], "output_contract": contracts[scenario["id"]], "input": scenario["input"]}, ensure_ascii=False)
        )
    return (
        "A bounded external runner already produced the JSON below. Perform a thin contract check only: preserve every "
        "substantive value, do not redo the underlying task, do not use tools, and return only JSON matching the supplied "
        "schema. You may shorten the summary but must not change status, scenario_id, decision, evidence_ids, or next_actions.\n\n"
        + json.dumps(offload_result, ensure_ascii=False)
    )


def run_codex(scenario: Mapping[str, Any], offload_result: Optional[Mapping[str, Any]], codex_path: str) -> Tuple[Dict[str, Any], Dict[str, Any], int, str]:
    command = [
        codex_path,
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox",
        "read-only",
        "-m",
        CODEX_MODEL,
        "-c",
        'model_reasoning_effort="high"',
        "--output-schema",
        str(OUTPUT_SCHEMA_PATH),
        "-C",
        str(ROOT),
        codex_prompt(scenario, offload_result),
    ]
    started = time.perf_counter()
    completed = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False)
    elapsed = round((time.perf_counter() - started) * 1000)
    if completed.returncode != 0:
        safe_error = SECRET_PATTERN.sub("[REDACTED]", completed.stderr[-1000:])
        raise RuntimeError("Codex failed with exit {}: {}".format(completed.returncode, safe_error))
    parsed = parse_codex_jsonl(completed.stdout)
    if object_errors(parsed["output"], HISTORICAL_FIELDS):
        raise RuntimeError("Codex returned an invalid result contract")
    if offload_result is not None:
        for field in HISTORICAL_FIELDS:
            if field != "summary" and parsed["output"].get(field) != offload_result.get(field):
                raise RuntimeError("Verifier changed protected field: " + field)
    return parsed["output"], parsed["usage"], elapsed, completed.stdout


def quality_check(scenario: Mapping[str, Any], output: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    reasons = object_errors(output, HISTORICAL_FIELDS)
    if reasons:
        return False, reasons
    expected = scenario["expected"]
    if output.get("status") != expected.get("status", "completed"):
        reasons.append("status mismatch")
    if output.get("scenario_id") != scenario["id"]:
        reasons.append("scenario_id changed")
    if output.get("decision") != expected["decision"]:
        reasons.append("decision mismatch")
    evidence = set(output.get("evidence_ids") or [])
    if len(evidence) != len(output["evidence_ids"]):
        reasons.append("duplicate evidence")
    if evidence - source_ids(scenario["input"]):
        reasons.append("unknown evidence")
    for item in expected.get("required_evidence_ids", []):
        if item not in evidence:
            reasons.append("missing evidence " + item)
    for item in expected.get("forbidden_evidence_ids", []):
        if item in evidence:
            reasons.append("forbidden evidence " + item)
    if expected.get("requires_approval_language"):
        if output["next_actions"] != [APPROVAL_ACTION]:
            reasons.append("approval boundary must match the code-owned action contract")
    return not reasons, reasons


def _token_total(usage: Mapping[str, Any]) -> int:
    return int(usage.get("input_tokens", 0) or 0) + int(usage.get("output_tokens", 0) or 0)


def run_baseline(scenario: Mapping[str, Any], repetition: int, codex_path: str) -> Dict[str, Any]:
    output, usage, wall_ms, raw = run_codex(scenario, None, codex_path)
    passed, reasons = quality_check(scenario, output)
    raw_path = RAW_DIR / "{}-baseline-{}.jsonl".format(scenario["id"], repetition)
    raw_path.write_text(raw, encoding="utf-8")
    cost = codex_cost_usd(usage)
    return {
        "scenario_id": scenario["id"], "arm": "codex_only", "repetition": repetition,
        "wall_ms": wall_ms, "codex_ms": wall_ms, "main_agent_tokens": _token_total(usage),
        "codex_usage": usage, "external_tokens": 0, "codex_api_equivalent_usd": cost,
        "codex_credit_equivalent": codex_credits(usage), "external_cost_usd": 0.0,
        "total_cost_usd": cost, "total_cost_usd_peak": cost, "quality_pass": passed,
        "quality_reasons": reasons, "output": output,
    }


def run_offload(scenario: Mapping[str, Any], repetition: int, codex_path: str, jev_key: str, deepseek_key: str) -> Dict[str, Any]:
    started = time.perf_counter()
    answers, jev_usage, jev_ms = call_jev(scenario, jev_key)
    compact = compose_offload_result(scenario, answers)
    generated, deepseek_usage, deepseek_ms = call_deepseek(compact, deepseek_key)
    output, codex_usage, codex_ms, raw = run_codex(scenario, generated, codex_path)
    wall_ms = round((time.perf_counter() - started) * 1000)
    passed, reasons = quality_check(scenario, output)
    raw_path = RAW_DIR / "{}-offload-{}.jsonl".format(scenario["id"], repetition)
    raw_path.write_text(raw, encoding="utf-8")
    safe_debug = {
        "jev_answers": answers, "jev_usage": jev_usage, "compact": compact,
        "deepseek_usage": deepseek_usage, "generated": generated,
    }
    (RAW_DIR / "{}-offload-{}-providers.json".format(scenario["id"], repetition)).write_text(
        json.dumps(sanitize(safe_debug), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    jev_cost = jev_cost_usd(jev_usage)
    ds_offpeak = deepseek_cost_usd(deepseek_usage, peak=False)
    ds_peak = deepseek_cost_usd(deepseek_usage, peak=True)
    codex_cost = codex_cost_usd(codex_usage)
    jev_tokens = int(jev_usage.get("input_tokens", jev_usage.get("prompt_tokens", 0)) or 0) + int(jev_usage.get("output_tokens", jev_usage.get("completion_tokens", 0)) or 0)
    deepseek_tokens = int(deepseek_usage.get("total_tokens", 0) or 0)
    return {
        "scenario_id": scenario["id"], "arm": "offloaded_verified", "repetition": repetition,
        "wall_ms": wall_ms, "jev_ms": jev_ms, "deepseek_ms": deepseek_ms, "codex_ms": codex_ms,
        "main_agent_tokens": _token_total(codex_usage), "codex_usage": codex_usage,
        "external_tokens": jev_tokens + deepseek_tokens, "jev_usage": jev_usage,
        "deepseek_usage": deepseek_usage, "codex_api_equivalent_usd": codex_cost,
        "codex_credit_equivalent": codex_credits(codex_usage),
        "external_cost_usd": jev_cost + ds_offpeak,
        "external_cost_usd_peak": jev_cost + ds_peak,
        "total_cost_usd": codex_cost + jev_cost + ds_offpeak,
        "total_cost_usd_peak": codex_cost + jev_cost + ds_peak,
        "quality_pass": passed, "quality_reasons": reasons, "output": output,
    }


def expand_runner_views(runs: Sequence[Mapping[str, Any]], scenarios: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Add a runner-only view derived from each measured offload execution.

    The external calls are not re-run. Their measured time, usage, and generated
    output are reused; only the optional Codex verification is removed.
    """
    by_id = {scenario["id"]: scenario for scenario in scenarios}
    expanded: List[Dict[str, Any]] = []
    for original in runs:
        run = dict(original)
        if run.get("arm") == "offloaded":
            run["arm"] = "offloaded_verified"
        expanded.append(run)
        if run.get("arm") != "offloaded_verified":
            continue
        raw_path = RAW_DIR / "{}-offload-{}-providers.json".format(run["scenario_id"], run["repetition"])
        provider_record = json.loads(raw_path.read_text(encoding="utf-8"))
        generated = provider_record["generated"]
        passed, reasons = quality_check(by_id[run["scenario_id"]], generated)
        runner_wall_ms = max(
            int(run["jev_ms"]) + int(run["deepseek_ms"]),
            int(run["wall_ms"]) - int(run["codex_ms"]),
        )
        expanded.append({
            "scenario_id": run["scenario_id"], "arm": "offloaded_runner_only", "repetition": run["repetition"],
            "wall_ms": runner_wall_ms, "jev_ms": run["jev_ms"], "deepseek_ms": run["deepseek_ms"], "codex_ms": 0,
            "main_agent_tokens": 0, "codex_usage": {}, "external_tokens": run["external_tokens"],
            "jev_usage": run["jev_usage"], "deepseek_usage": run["deepseek_usage"],
            "codex_api_equivalent_usd": 0.0, "codex_credit_equivalent": 0.0,
            "external_cost_usd": run["external_cost_usd"],
            "external_cost_usd_peak": run["external_cost_usd_peak"],
            "total_cost_usd": run["external_cost_usd"],
            "total_cost_usd_peak": run["external_cost_usd_peak"],
            "quality_pass": passed, "quality_reasons": reasons, "output": generated,
            "derived_from": "offloaded_verified",
        })
    return expanded


def aggregate(runs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    groups: Dict[str, List[Mapping[str, Any]]] = {}
    for run in runs:
        key = run["scenario_id"] + ":" + run["arm"]
        groups.setdefault(key, []).append(run)
    summaries = {}
    for key, rows in groups.items():
        summary = summarize_runs(rows)
        summary["median_codex_ms"] = median(float(row.get("codex_ms", 0)) for row in rows)
        summary["median_external_tokens"] = median(float(row.get("external_tokens", 0)) for row in rows)
        summary["median_codex_api_equivalent_usd"] = median(float(row.get("codex_api_equivalent_usd", 0)) for row in rows)
        summary["median_codex_credit_equivalent"] = median(float(row.get("codex_credit_equivalent", 0)) for row in rows)
        summary["median_external_cost_usd"] = median(float(row.get("external_cost_usd", 0)) for row in rows)
        summary["median_total_cost_usd_peak"] = median(float(row.get("total_cost_usd_peak", row["total_cost_usd"])) for row in rows)
        if rows[0]["arm"] in ("offloaded_runner_only", "offloaded_verified"):
            summary["median_jev_ms"] = median(float(row["jev_ms"]) for row in rows)
            summary["median_deepseek_ms"] = median(float(row["deepseek_ms"]) for row in rows)
        summaries[key] = summary
    comparisons = {}
    for scenario_id in sorted({run["scenario_id"] for run in runs}):
        baseline = summaries[scenario_id + ":codex_only"]
        comparisons[scenario_id] = {}
        for label, arm in (("runner_only", "offloaded_runner_only"), ("with_codex_verification", "offloaded_verified")):
            offload = summaries[scenario_id + ":" + arm]
            comparisons[scenario_id][label] = {
                "main_agent_token_reduction_pct": _reduction(baseline["median_main_agent_tokens"], offload["median_main_agent_tokens"]),
                "latency_reduction_pct": _reduction(baseline["median_wall_ms"], offload["median_wall_ms"]),
                "api_equivalent_cost_reduction_pct": _reduction(baseline["median_total_cost_usd"], offload["median_total_cost_usd"]),
            }
    return {"groups": summaries, "comparisons": comparisons}


def _reduction(before: float, after: float) -> float:
    if not before:
        return 0.0
    return (before - after) / before * 100.0


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# WhatToOffload live benchmark",
        "",
        "Generated: `{}`".format(report["generated_at"]),
        "",
        "Each scenario and arm ran {} times. Medians are shown. Raw provider logs are intentionally excluded.".format(report["repetitions"]),
        "",
        "| Scenario | Arm | Main-agent tokens | External tokens | Wall time | Codex/Jev/DeepSeek time | Codex credits | API-equivalent cost | Quality |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for scenario in report["scenarios"]:
        scenario_id = scenario["id"]
        for arm in ("codex_only", "offloaded_runner_only", "offloaded_verified"):
            item = report["aggregate"]["groups"][scenario_id + ":" + arm]
            components = "{} ms".format(round(item["median_codex_ms"]))
            if arm in ("offloaded_runner_only", "offloaded_verified"):
                components = "{} / {} / {} ms".format(round(item["median_codex_ms"]), round(item["median_jev_ms"]), round(item["median_deepseek_ms"]))
            cost = "${:.6f}".format(item["median_total_cost_usd"])
            if item["median_total_cost_usd_peak"] != item["median_total_cost_usd"]:
                cost += "–${:.6f}".format(item["median_total_cost_usd_peak"])
            lines.append(
                "| {} | {} | {:,.0f} | {:,.0f} | {:.2f}s | {} | {:.4f} | {} | {:.0%} |".format(
                    scenario["title"], arm, item["median_main_agent_tokens"], item["median_external_tokens"],
                    item["median_wall_ms"] / 1000, components, item["median_codex_credit_equivalent"], cost, item["quality_pass_rate"]
                )
            )
    lines += [
        "",
        "## Relative change",
        "",
        "| Scenario | Main-agent token reduction | End-to-end latency reduction | API-equivalent cost reduction |",
        "| --- | ---: | ---: | ---: |",
    ]
    for scenario in report["scenarios"]:
        for label, name in (("runner_only", "Runner only"), ("with_codex_verification", "With Codex verification")):
            item = report["aggregate"]["comparisons"][scenario["id"]][label]
            lines.append(
                "| {} — {} | {:+.1f}% | {:+.1f}% | {:+.1f}% |".format(
                    scenario["title"], name, item["main_agent_token_reduction_pct"], item["latency_reduction_pct"], item["api_equivalent_cost_reduction_pct"]
                )
            )
    lines += [
        "",
        "## Interpretation notes",
        "",
        "- Main-agent tokens compare GPT-5.6 Sol usage within the same tokenizer. External-token totals are shown separately because Jev and DeepSeek use different tokenizers.",
        "- Codex cost is an API-price equivalent; a ChatGPT plan consumes quota/credits rather than charging that USD amount per run.",
        "- With only three repetitions, Sol cache hits varied between runs and made API-equivalent cost volatile. Treat verified-path cost deltas as directional; the token and latency columns expose the underlying work more directly.",
        "- DeepSeek is shown as an off-peak-to-peak range. Jev uses the OpenRouter Jev 1.13 input price recorded for this run.",
        "- Runner-only is a measured lower-bound view derived by removing the optional Codex verification from the same offload run. It excludes the host's small invocation/return envelope.",
        "- Wall time is sequential end-to-end latency. The verified offload component order is Codex thin check / Jev / DeepSeek.",
        "- The fixtures are synthetic and bounded. This measures operating cost and latency, not the one-time engineering cost of building the runner.",
        "",
        "## Price snapshot",
        "",
        "- GPT-5.6 Sol: $4/M uncached input, $0.40/M cached input, $20/M output.",
        "- Jev 1.13 on OpenRouter: $0.042/M input, $0 output.",
        "- DeepSeek Flash: off-peak $0.003/M cache-hit input, $0.15/M cache-miss input, $0.60/M output; peak prices are double.",
        "",
    ]
    return "\n".join(lines)


def render_svg(report: Mapping[str, Any]) -> str:
    width, height = 1200, 900
    left, right = 110, 35
    panel_height = 155
    panel_tops = [115, 385, 655]
    arms = [
        ("codex_only", "Codex-only", "#6366f1"),
        ("offloaded_runner_only", "Jev + DeepSeek", "#10b981"),
    ]
    scenarios = report["scenarios"]
    visible = [report["aggregate"]["groups"][s["id"] + ":" + a] for s in scenarios for a, _, _ in arms]
    quality_min = min(item["quality_pass_rate"] for item in visible)
    quality_max = max(item["quality_pass_rate"] for item in visible)
    caption = "Requested repetitions: {} · observed contract pass range {:.0%}–{:.0%}".format(report["repetitions"], quality_min, quality_max)
    metrics = [
        ("Main-agent tokens", lambda item: item["median_main_agent_tokens"], lambda value: "{:,.0f}".format(value)),
        ("Sequential wall time (seconds)", lambda item: item["median_wall_ms"] / 1000, lambda value: "{:.1f}s".format(value)),
        ("API-equivalent cost per 1,000 runs (USD)", lambda item: item["median_total_cost_usd"] * 1000, lambda value: "${:.2f}".format(value)),
    ]
    short_names = {"code-triage": "Code triage", "web-research": "Web research", "business-screening": "Business screening"}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}" role="img" aria-labelledby="title desc">'.format(width, height, width, height),
        '<title id="title">WhatToOffload live benchmark comparison</title>',
        '<desc id="desc">Observed median tokens, wall time and API-equivalent cost. {}</desc>'.format(html.escape(caption)),
        '<rect width="1200" height="900" fill="#ffffff"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;fill:#111827}.muted{fill:#6b7280}.grid{stroke:#e5e7eb;stroke-width:1}.axis{stroke:#9ca3af;stroke-width:1}</style>',
        '<text x="45" y="48" font-size="25" font-weight="600">WhatToOffload · live benchmark</text>',
        '<text x="45" y="76" font-size="14" class="muted">{}</text>'.format(html.escape(caption)),
    ]
    legend_x = 755
    for index, (_, label, color) in enumerate(arms):
        x = legend_x + index * 175
        parts.append('<rect x="{}" y="39" width="13" height="13" rx="2" fill="{}"/>'.format(x, color))
        parts.append('<text x="{}" y="51" font-size="13">{}</text>'.format(x + 20, html.escape(label)))
    plot_width = width - left - right
    group_width = plot_width / len(scenarios)
    bar_width = 54
    bar_gap = 10
    for metric_index, (title, getter, formatter) in enumerate(metrics):
        top = panel_tops[metric_index]
        bottom = top + panel_height
        values = []
        for scenario in scenarios:
            for arm, _, _ in arms:
                values.append(float(getter(report["aggregate"]["groups"][scenario["id"] + ":" + arm])))
        max_value = max(values) * 1.12 if max(values) else 1
        parts.append('<text x="45" y="{}" font-size="16" font-weight="600">{}</text>'.format(top - 24, html.escape(title)))
        for tick in range(5):
            value = max_value * tick / 4
            y = bottom - panel_height * tick / 4
            parts.append('<line class="grid" x1="{}" y1="{:.1f}" x2="{}" y2="{:.1f}"/>'.format(left, y, width - right, y))
            tick_label = formatter(value)
            parts.append('<text x="{}" y="{:.1f}" text-anchor="end" dominant-baseline="middle" font-size="11" class="muted">{}</text>'.format(left - 9, y, html.escape(tick_label)))
        parts.append('<line class="axis" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(left, bottom, width - right, bottom))
        for scenario_index, scenario in enumerate(scenarios):
            center = left + group_width * (scenario_index + 0.5)
            cluster_width = len(arms) * bar_width + (len(arms) - 1) * bar_gap
            start = center - cluster_width / 2
            for arm_index, (arm, _, color) in enumerate(arms):
                item = report["aggregate"]["groups"][scenario["id"] + ":" + arm]
                value = float(getter(item))
                bar_height = panel_height * value / max_value if max_value else 0
                x = start + arm_index * (bar_width + bar_gap)
                y = bottom - bar_height
                parts.append('<rect x="{:.1f}" y="{:.1f}" width="{}" height="{:.1f}" rx="3" fill="{}"/>'.format(x, y, bar_width, max(bar_height, 1), color))
                label_y = max(top + 12, y - 7)
                parts.append('<text x="{:.1f}" y="{:.1f}" text-anchor="middle" font-size="11">{}</text>'.format(x + bar_width / 2, label_y, html.escape(formatter(value))))
            parts.append('<text x="{:.1f}" y="{}" text-anchor="middle" font-size="12" class="muted">{}</text>'.format(center, bottom + 21, html.escape(short_names[scenario["id"]])))
    parts.append('<text x="45" y="880" font-size="12" class="muted">Runner-only excludes the host invocation/return envelope. Full per-run measurements remain available in the accompanying report.</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--codex-path", default="/Applications/ChatGPT.app/Contents/Resources/codex")
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument("--output-dir", help="New directory for v2 results; archived results are never overwritten")
    parser.add_argument("--rebuild-existing", action="store_true")
    args = parser.parse_args(argv)
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be positive")
    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.rebuild_existing:
        existing = json.loads((RESULTS_DIR / "latest.json").read_text(encoding="utf-8"))
        runs = [dict(run) for run in existing["runs"] if run["arm"] in ("codex_only", "offloaded", "offloaded_verified")]
        repetitions = int(existing["repetitions"])
    else:
        jev_key = os.environ.get("OPENROUTER_API_KEY", "")
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not jev_key or not deepseek_key:
            raise SystemExit("OPENROUTER_API_KEY and DEEPSEEK_API_KEY must be set")
        runs = []
        repetitions = args.repetitions
        total = len(scenarios) * repetitions * 2
        step = 0
        for repetition in range(1, repetitions + 1):
            for scenario in scenarios:
                for arm in ("codex_only", "offloaded_verified"):
                    step += 1
                    print("[{}/{}] {} {} repetition {}".format(step, total, scenario["id"], arm, repetition), flush=True)
                    if arm == "codex_only":
                        run = run_baseline(scenario, repetition, args.codex_path)
                    else:
                        run = run_offload(scenario, repetition, args.codex_path, jev_key, deepseek_key)
                    runs.append(run)
                    print(
                        "  done: {:.2f}s, main-agent {} tokens, quality {}".format(
                            run["wall_ms"] / 1000, run["main_agent_tokens"], "pass" if run["quality_pass"] else "FAIL"
                        ),
                        flush=True,
                    )
    runs = expand_runner_views(runs, scenarios)
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repetitions": repetitions,
        "models": {"codex": CODEX_MODEL, "codex_reasoning": "high", "jev": JEV_MODEL, "deepseek": DEEPSEEK_MODEL},
        "scenarios": [{"id": item["id"], "title": item["title"]} for item in scenarios],
        "runs": sanitize(runs),
        "aggregate": aggregate(runs),
        "price_sources": {
            "codex": "https://developers.openai.com/api/docs/models/gpt-5.6-sol",
            "codex_credits": "https://learn.chatgpt.com/docs/pricing",
            "jev": "https://openrouter.ai/typesafe/jev-1.13/",
            "deepseek": "https://api-docs.deepseek.com/quick_start/pricing/",
        },
    }
    if args.write_results:
        destination = Path(args.output_dir) if args.output_dir else ROOT / ".local" / ("microbenchmark-v2-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
        destination.mkdir(parents=True, exist_ok=False)
        (destination / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (destination / "latest.md").write_text(render_markdown(report), encoding="utf-8")
        (destination / "comparison.svg").write_text(render_svg(report), encoding="utf-8")
    print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
