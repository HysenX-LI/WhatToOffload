"""Offline reproduction, frozen live matrix, construction comparison and reporting."""
import argparse
import hashlib
import json
import platform
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .evaluate import audit_gold, grade
from .contracts import result_errors
from .experiments import REPO, ROOT, construct, run_agent, run_candidate
from .providers import OfflineJudge, SemanticJudge, live_client
from .report import write_report
from .runner import screen
from .sandbox import preflight


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def load_split(split):
    base = ROOT / "data" / split
    cases, answers = read(base / "inputs.json"), read(base / "gold.json")
    audit_gold(cases, answers)
    return cases, answers


def snapshot():
    paths = [REPO / "SKILL.md", REPO / "benchmarks/contracts.py"]
    paths += [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in (".py", ".md", ".json")
              and "results" not in p.relative_to(ROOT).parts and not p.name.startswith("freeze-")]
    for directory in ("references", "assets/templates", "examples"):
        paths += [p for p in (REPO / directory).rglob("*") if p.is_file()]
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def freeze(path):
    path = Path(path)
    if path.exists():
        raise ValueError("freeze already exists; never overwrite a frozen experiment")
    for split in ("dev", "final"):
        load_split(split)
    value = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
             "final_status": "not executed at freeze", "files": snapshot()}
    # Freeze files must not recursively hash themselves.
    value["files"].pop(str(path.resolve().relative_to(REPO)), None) if path.resolve().is_relative_to(REPO) else None
    dump(path, value)
    return value


def verify_freeze(path):
    frozen = read(path)
    if snapshot() != frozen["files"]:
        raise ValueError("frozen implementation/data changed; do not reuse final data after outcome-driven changes")
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def matrix(split, repetitions, config):
    cases, _ = load_split(split)
    vendors = sum(len(c["vendors"]) for c in cases)
    a = len(cases) * repetitions * 2 * config["agent_turns"] + vendors * repetitions
    b = 2 * repetitions * config["build_turns"] + 2 * repetitions * vendors
    per_call = ((config["max_input_bytes"] + 8192) * config["input_usd_per_million"] + config["max_output_tokens"] * config["output_usd_per_million"]) / 1_000_000
    return {"split": split, "cases": len(cases), "vendor_records": vendors, "repetitions": repetitions,
            "execution": {"arms": ["agent_direct", "agent_task_skill", "prepared_runner"], "attempts": 3*len(cases)*repetitions, "max_http_calls": a},
            "construction": {"arms": ["build_without_skill", "build_with_skill"], "builds": 2*repetitions, "candidate_evaluations": 2*len(cases)*repetitions, "max_http_calls": b},
            "max_http_calls_both": a+b, "configured_request_cap": config["max_calls"],
            "configured_usd_reservation_cap": config["budget_usd"], "per_request_reservation_usd": per_call,
            "worst_case_reserved_usd_before_global_caps": (a+b)*per_call,
            "rates_are_verified": config["rates_verified"], "model": config["model"],
            "cost_basis": "operator-verified upper-rate estimate; not an invoice", "live_executed": False}


def planned_attempts(cases, repetitions, arms):
    result = [{"attempt_id": "{}:{}:{}".format(arm, c["request_id"], rep), "arm": arm,
               "case_id": c["request_id"], "repetition": rep}
              for rep in range(1, repetitions+1) for c in cases for arm in arms]
    random.Random(20260920).shuffle(result)
    return result


def failure_record(plan, payload, gold, error):
    return dict(plan, output=None, error=error, execution_status="failed", wall_ms=None,
                cost_usd=None, calls=[], runnable=False, grade=grade(payload, None, gold))


def regenerate(directory):
    directory = Path(directory)
    metadata = read(directory / "metadata.json")
    plan = read(directory / "plan.json")
    actual = {}
    path = directory / "attempts.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # truncated interrupted write stays failed in the schedule
            actual[record["attempt_id"]] = record
    records = [actual.get(p["attempt_id"]) or dict(p, output=None, error="interrupted_or_not_executed",
               execution_status="failed", wall_ms=None, cost_usd=None, calls=[], runnable=False, grade=p["failure_grade"]) for p in plan]
    write_report(directory, records, metadata)
    # Construction investment and runnability remain separate from task-quality statistics.
    builds = []
    for path in sorted((directory / "builds").glob("*/build.json")):
        record = read(path)
        selected = [r for r in records if r["arm"] == record["arm"] and r["repetition"] == record["repetition"]]
        record["candidate_cases_executed"] = sum(r["execution_status"] == "completed" for r in selected)
        record["candidate_cases_runnable"] = sum(r.get("runnable", False) for r in selected)
        record["candidate_cases_planned"] = len(selected)
        record["candidate_cases_correct"] = sum(r["grade"]["passed"] for r in selected)
        builds.append(record)
    dump(directory / "construction.json", {"builds": builds, "executed": bool(builds), "human_rework": "unknown unless independently measured"})
    lines = ["# Construction comparison", "", "Build investment is separate from candidate execution. Human rework is unknown, not zero.", "",
             "| Arm | Repeat | Build status | Syntax | Runnable cases | Correct cases | Boundary decisions | Build ms | Build USD |",
             "|---|---:|---|---|---|---|---|---:|---:|"]
    for b in builds:
        lines.append("| {} | {} | {} | {} | {}/{} | {}/{} | {}/{} | {} | {} |".format(
            b["arm"], b["repetition"], b["status"], b["syntax_valid"], b["candidate_cases_runnable"], b["candidate_cases_planned"],
            b["candidate_cases_correct"], b["candidate_cases_planned"], b["boundary_correct"], b["boundary_total"], b["wall_ms"],
            "unknown" if b["cost_usd"] is None else "{:.6f}".format(b["cost_usd"])))
    if not builds:
        lines.append("\nNot executed. Offline runner checks provide no evidence of Skill construction benefit.")
    (directory / "construction.md").write_text("\n".join(lines) + "\n")
    return records


def run(args):
    if args.live and not args.config:
        raise ValueError("--live requires --config")
    if not args.live and args.study != "execution":
        raise ValueError("offline mode measures prepared runner software only; construction agents are unexecuted")
    cases, answers = load_split(args.split)
    freeze_hash = verify_freeze(args.freeze) if args.freeze else None
    if args.split == "final" and not freeze_hash:
        raise ValueError("final evaluation requires a verified --freeze")
    if args.split == "final" and args.study == "construction" and not args.live:
        raise ValueError("formal construction requires live agents")
    client = None
    config = None
    image_id = None
    if args.live:
        config = read(args.config)
        image_id = preflight(config["docker_image"])
        client = live_client(args.config)
    arms = ["prepared_runner"] if not args.live else []
    if args.live and args.study in ("execution", "both"):
        arms += ["agent_direct", "agent_task_skill", "prepared_runner"]
    if args.live and args.study in ("construction", "both"):
        arms += ["build_without_skill", "build_with_skill"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    meta = {"schema_version": 1, "run_id": out.name, "mode": "live" if args.live else "offline",
            "split": args.split, "study": args.study, "repetitions": args.repetitions,
            "created_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "freeze_sha256": freeze_hash, "source_hashes": snapshot(), "docker_image_id": image_id,
            "live_config": config, "preparation_cost_usd": None,
            "model_quality_measured": bool(args.live), "cost_basis": "upper-rate estimate" if args.live else "zero provider calls; production cost unknown"}
    dump(out / "metadata.json", meta)
    plan = planned_attempts(cases, args.repetitions, arms)
    by_id = {c["request_id"]: c for c in cases}
    for item in plan:
        item["failure_grade"] = grade(by_id[item["case_id"]], None, answers[item["case_id"]]["result"])
    dump(out / "plan.json", plan)
    built = {}
    try:
        if args.live and args.study in ("construction", "both"):
            dev, _ = load_split("dev")
            workflow_gold = read(ROOT / "data/workflow_gold.json")
            for rep in range(1, args.repetitions+1):
                # Alternate construction order between paired repetitions.
                for with_skill in ([False, True] if rep % 2 else [True, False]):
                    arm = "build_with_skill" if with_skill else "build_without_skill"
                    destination = out / "builds" / (arm + "-" + str(rep))
                    build = construct(client, dev, with_skill, destination)
                    build["repetition"] = rep
                    decisions = build.get("boundary_decisions")
                    mapping = {v.get("id"): v.get("decision") for v in decisions if isinstance(v, dict)} if isinstance(decisions, list) else {}
                    build["boundary_correct"] = sum(mapping.get(k) == v for k, v in workflow_gold.items())
                    build["boundary_total"] = len(workflow_gold)
                    dump(destination / "build.json", build)
                    built[(arm, rep)] = (build, destination)
        with (out / "attempts.jsonl").open("a", encoding="utf-8") as handle:
            for item in plan:
                payload = by_id[item["case_id"]]
                record = failure_record(item, payload, answers[item["case_id"]]["result"], "not_started")
                before = len(client.calls) if client else 0
                started = time.perf_counter()
                try:
                    if item["arm"] == "prepared_runner":
                        output = screen(payload, SemanticJudge(client) if client else OfflineJudge())
                    elif item["arm"] in ("agent_direct", "agent_task_skill"):
                        output = run_agent(payload, client, item["arm"] == "agent_task_skill")
                    else:
                        build, destination = built[(item["arm"], item["repetition"])]
                        if build["status"] != "completed":
                            raise RuntimeError("construction_failed")
                        output = run_candidate(payload, (destination / "candidate.py").read_text(), build["candidate_sha256"], client)
                    record["output"] = output
                    record["grade"] = grade(payload, output, answers[item["case_id"]]["result"])
                    record["runnable"] = not result_errors(payload, output)
                    record["execution_status"] = "failed" if result_errors(payload, output) or output.get("status") == "failed" else "completed"
                    record["error"] = None if record["execution_status"] == "completed" else "executor_reported_failure"
                except Exception as exc:
                    record["error"] = type(exc).__name__
                finally:
                    record["wall_ms"] = round((time.perf_counter() - started) * 1000, 3)
                    record["calls"] = client.calls[before:] if client else []
                    costs = [c["cost_usd"] for c in record["calls"]]
                    record["cost_usd"] = sum(costs) if all(c is not None for c in costs) else None
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    handle.flush()
                    if client:
                        dump(out / "calls.json", {"calls": client.calls, "reserved_usd": client.reserved_usd})
    finally:
        regenerate(out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--live", action="store_true")
    p.add_argument("--config")
    p.add_argument("--split", choices=("dev", "final"), default="dev")
    p.add_argument("--study", choices=("execution", "construction", "both"), default="execution")
    p.add_argument("--repetitions", type=int, default=1)
    p.add_argument("--freeze")
    p.add_argument("--out", required=True)
    p = sub.add_parser("freeze")
    p.add_argument("--out", required=True)
    p = sub.add_parser("verify")
    p.add_argument("--freeze", required=True)
    p = sub.add_parser("matrix")
    p.add_argument("--config", default=str(ROOT / "live-config.example.json"))
    p.add_argument("--split", choices=("dev", "final"), default="final")
    p.add_argument("--repetitions", type=int, default=1)
    p = sub.add_parser("report")
    p.add_argument("--run", required=True)
    args = parser.parse_args()
    try:
        if getattr(args, "repetitions", 1) < 1:
            raise ValueError("repetitions must be positive")
        if args.command == "run":
            destination = run(args)
            print(destination)
            if not all(r["grade"]["passed"] for r in read(destination / "report.json")["records"]):
                parser.exit(1, "Some attempts failed acceptance; all results retained.\n")
        elif args.command == "freeze":
            freeze(args.out)
            print(args.out)
        elif args.command == "verify":
            print(verify_freeze(args.freeze))
        elif args.command == "matrix":
            print(json.dumps(matrix(args.split, args.repetitions, read(args.config)), indent=2))
        else:
            regenerate(args.run)
            print(Path(args.run) / "report.md")
    except (ValueError, RuntimeError, FileExistsError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    main()
