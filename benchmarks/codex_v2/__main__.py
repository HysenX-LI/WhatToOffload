"""Offline regression and ChatGPT-Codex experiments. No API-key/price options."""
import argparse
import hashlib
import json
import platform
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmarks.public_v1.__main__ import load_split, snapshot as legacy_snapshot
from benchmarks.public_v1.contracts import result_errors
from benchmarks.public_v1.evaluate import grade
from benchmarks.public_v1.runner import screen
from .report import regenerate
from .export import export_run
from .runtime import ROOT, REPO, CodexClient, StopRun, preflight, validate_config
from .studies import DATA_ROOT, OfflineJudge, CodexJudge, run_agent, construct, run_candidate


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def snapshot():
    files = legacy_snapshot()
    paths = list(ROOT.glob("*.py")) + [ROOT / "PROTOCOL.md", ROOT / "config.json"]
    files.update({str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    return files


def freeze(path):
    if Path(path).exists():
        raise ValueError("never overwrite a freeze")
    for split in ("dev", "final"):
        load_split(split)  # schema/arithmetic audit only; not executor use
    exposure = read(ROOT / "EXPOSURE.json")
    if exposure["status"] != "not_executed":
        raise ValueError("final split is already exposed; retain the original freeze for repeats or author a new split")
    dump(path, {"version": "codex-v2", "created_at": datetime.now(timezone.utc).isoformat(),
                "final_status_at_freeze": exposure["status"], "files": snapshot()})


def verify(path):
    if read(path)["files"] != snapshot():
        raise ValueError("frozen sources changed; do not reuse final after outcome-driven changes")
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def matrix(config, split="final", limit=None):
    cases, _ = load_split(split)
    if limit: cases = cases[:limit]
    n, v = len(cases), sum(len(c["vendors"]) for c in cases)
    return {"model": config["model"], "reasoning_effort": config["reasoning_effort"], "authentication": "ChatGPT",
            "cases": n, "vendor_records": v, "repetitions": 1, "execution_attempts": n*3, "candidate_attempts": n*2,
            "builds": 2, "max_Codex_invocations_before_global_cap": 2*n + v*3 + 2,
            "global_call_cap": config["max_calls"], "global_timeout_seconds": config["total_timeout_seconds"],
            "agent_timeout_seconds": config["agent_timeout_seconds"], "build_timeout_seconds": config["build_timeout_seconds"],
            "semantic_timeout_seconds": config["semantic_timeout_seconds"], "max_tools_per_call": config["max_tools_per_call"],
            "billing_cost": None, "independently_billed_API_calls": 0, "underlying_model_request_count": None}


def run(args):
    config = validate_config(read(args.config))
    if args.mode == "simulation" and args.study != "execution":
        raise ValueError("simulation cannot measure construction")
    if args.split == "final" and (not args.freeze or args.limit):
        raise ValueError("final requires freeze and full split")
    if args.split == "final" and config != read(ROOT / "config.json"):
        raise ValueError("final config must match the configuration in the frozen source manifest")
    freeze_hash = verify(args.freeze) if args.freeze else None
    cases, gold = load_split(args.split)
    if args.limit: cases = cases[:args.limit]
    system = preflight(config) if args.mode == "codex" else None
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    client = CodexClient(config, out / "calls") if args.mode == "codex" else None
    arms = ["prepared_runner"] if not client else []
    if client and args.study in ("execution", "both"):
        arms += ["agent_direct", "agent_task_skill", "prepared_runner"]
    if client and args.study in ("construction", "both"):
        arms += ["build_without_skill", "build_with_skill"]
    plan = [{"attempt_id": arm+":"+c["request_id"]+":1", "arm": arm, "case_id": c["request_id"], "repetition": 1,
             "failure_grade": grade(c, None, gold[c["request_id"]]["result"])} for arm in arms for c in cases]
    random.Random(20260920).shuffle(plan)
    meta = {"version": "codex-v2", "run_id": out.name, "mode": args.mode, "split": args.split, "study": args.study,
            "created_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(), "system": system,
            "config": config, "freeze_sha256": freeze_hash, "source_hashes": snapshot(), "stop_reason": None,
            "billing_cost": None, "preparation_cost": None, "repetitions": 1, "final_exposure_started": False}
    meta["workflow_probe_count"] = len(read(DATA_ROOT / "data/workflows.json"))
    dump(out / "metadata.json", meta); dump(out / "plan.json", plan)
    built, by_id = {}, {c["request_id"]: c for c in cases}
    try:
        if client and args.study in ("construction", "both"):
            dev, _ = load_split("dev")
            boundary = read(DATA_ROOT / "data/workflow_gold.json")
            for with_skill in (False, True):
                client.check()
                arm = "build_with_skill" if with_skill else "build_without_skill"
                destination = out / "builds" / arm
                print("BUILD " + arm, flush=True)
                b = construct(client, dev, with_skill, destination)
                decisions = b.get("boundary_decisions")
                mapping = {d.get("id"): d.get("decision") for d in decisions if isinstance(d, dict)} if isinstance(decisions, list) else {}
                b.update(boundary_correct=sum(mapping.get(k) == v for k, v in boundary.items()), boundary_total=len(boundary))
                dump(destination / "build.json", b)
                built[arm] = (b, destination)
                if client.stop_reason: raise StopRun(client.stop_reason)
        with (out / "attempts.jsonl").open("a") as handle:
            for item in plan:
                if client: client.check()
                payload = by_id[item["case_id"]]
                record = dict(item, output=None, error=None, execution_status="failed", wall_ms=None, cost_usd=None,
                              calls=[], runnable=False, grade=item["failure_grade"])
                if args.split == "final":
                    if not meta["final_exposure_started"]:
                        exposure = read(ROOT / "EXPOSURE.json")
                        exposure["status"] = "exposed"
                        exposure["runs"].append({"run_id": out.name, "freeze_sha256": freeze_hash,
                                                 "first_exposure_at": datetime.now(timezone.utc).isoformat()})
                        dump(ROOT / "EXPOSURE.json", exposure)
                    meta["final_exposure_started"] = True
                    dump(out / "metadata.json", meta)
                print("RUN " + item["attempt_id"], flush=True)
                before, started = len(client.calls) if client else 0, time.perf_counter()
                try:
                    if item["arm"] == "prepared_runner":
                        output = screen(payload, CodexJudge(client) if client else OfflineJudge())
                    elif item["arm"] in ("agent_direct", "agent_task_skill"):
                        output = run_agent(payload, client, item["arm"] == "agent_task_skill")
                    else:
                        b, dest = built[item["arm"]]
                        if b["status"] != "completed": raise ValueError("construction_failed")
                        output = run_candidate(payload, (dest / "candidate.py").read_text(), b["candidate_sha256"], client)
                    record["output"] = output
                    record["runnable"] = not result_errors(payload, output)
                    record["execution_status"] = "completed" if record["runnable"] and output["status"] != "failed" else "failed"
                    if record["execution_status"] == "failed": record["error"] = "executor_reported_failure"
                except Exception as exc:
                    record["error"] = str(exc) if isinstance(exc, StopRun) else type(exc).__name__
                    if isinstance(exc, StopRun) and client: client.stop_reason = str(exc)
                finally:
                    # Stop timer before independent evaluation; failure timing is retained too.
                    record["wall_ms"] = round((time.perf_counter()-started)*1000, 3)
                    record["calls"] = client.calls[before:] if client else []
                    record["grade"] = grade(payload, record["output"], gold[item["case_id"]]["result"])
                    handle.write(json.dumps(record, ensure_ascii=False)+"\n"); handle.flush()
                    print("RESULT {} {} {}".format(item["attempt_id"], record["execution_status"], record["grade"]["passed"]), flush=True)
                if client and client.stop_reason: raise StopRun(client.stop_reason)
    except StopRun as exc:
        meta["stop_reason"] = str(exc)
    finally:
        meta["finished_at"] = datetime.now(timezone.utc).isoformat()
        dump(out / "metadata.json", meta)
        result = regenerate(out)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--mode", choices=("simulation", "codex"), default="simulation")
    p.add_argument("--study", choices=("execution", "construction", "both"), default="execution")
    p.add_argument("--split", choices=("dev", "final"), default="dev")
    p.add_argument("--limit", type=int)
    p.add_argument("--config", default=str(ROOT / "config.json"))
    p.add_argument("--freeze")
    p.add_argument("--out", required=True)
    p = sub.add_parser("freeze"); p.add_argument("--out", required=True)
    p = sub.add_parser("verify"); p.add_argument("--freeze", required=True)
    p = sub.add_parser("matrix"); p.add_argument("--config", default=str(ROOT / "config.json"))
    p = sub.add_parser("report"); p.add_argument("--run", required=True)
    p = sub.add_parser("preflight"); p.add_argument("--config", default=str(ROOT / "config.json"))
    p = sub.add_parser("export"); p.add_argument("--run", required=True); p.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.command == "run":
        result = run(args)
        print(json.dumps(result["all_measurements"], indent=2))
        if not all(r["grade"]["passed"] for r in result["records"]): parser.exit(1, "Incomplete/failed acceptance; records retained.\n")
    elif args.command == "freeze": freeze(args.out)
    elif args.command == "verify": print(verify(args.freeze))
    elif args.command == "matrix": print(json.dumps(matrix(validate_config(read(args.config))), indent=2))
    elif args.command == "report": regenerate(args.run)
    elif args.command == "preflight": print(json.dumps(preflight(validate_config(read(args.config))), indent=2))
    elif args.command == "export": export_run(args.run, args.out)


if __name__ == "__main__":
    main()
