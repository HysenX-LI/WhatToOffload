"""Only the predeclared three execution arms and two construction arms."""
import ast
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

from . import sandbox
from .providers import SemanticJudge

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
TOOL = [{"type": "function", "function": {"name": "python", "description": "Run Python in the isolated workspace; read/write files and use standard libraries. No network.",
        "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"], "additionalProperties": False}}}]
EXECUTION_SYSTEM = "Complete TASK.md for input.json. Tools and scripts are allowed. Write the final JSON to result.json, then finish. Never read outside the supplied workspace."
BUILD_SYSTEM = (
    "Design and implement the TASK.md runner using development inputs in dev_inputs.json. No reference answers are available. "
    "You are authorized to choose a bounded design and implement it now, with standard Python and the provided helpers. "
    "Do not call paid/external APIs during construction. Use fake judgments for your own tests. "
    "Create self-contained candidate.py with importable screen(payload, judge); CLI reads one JSON line and uses semantic_bridge.judge. "
    "Also write offload_decisions.json: for each workflow in workflows.json, {id,decision:offload|keep_agent,reason}. "
    "Only candidate.py and offload_decisions.json will be retained; helpers.py and semantic_bridge.py are restored to original versions. "
    "Finish within the allocated tool/model turns; human assistance and extra packages are unavailable."
)


def common_workspace(path):
    path = Path(path)
    for name in ("TASK.md", "helpers.py", "semantic_bridge.py"):
        shutil.copyfile(ROOT / name, path / name)


def build_workspace(path, dev_cases, with_skill):
    common_workspace(path)
    path = Path(path)
    (path / "dev_inputs.json").write_text(json.dumps(dev_cases))
    shutil.copyfile(ROOT / "data/workflows.json", path / "workflows.json")
    if with_skill:
        shutil.copyfile(REPO / "SKILL.md", path / "SKILL.md")
        for directory in ("references", "assets/templates", "examples"):
            shutil.copytree(REPO / directory, path / directory)


def agent_loop(client, workspace, system, max_turns):
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": "Begin. The task and allowed material are in the working directory."}]
    tool_calls = 0
    for _ in range(max_turns):
        message = client.complete(messages, TOOL)
        messages.append({k: message[k] for k in ("role", "content", "tool_calls") if k in message})
        messages[-1]["role"] = "assistant"
        calls = message.get("tool_calls") or []
        if not calls:
            return tool_calls
        if len(calls) > 4:
            raise RuntimeError("tool_batch_limit")
        for call in calls:
            tool_calls += 1
            try:
                if call["function"]["name"] != "python":
                    raise ValueError("unknown tool")
                args = json.loads(call["function"]["arguments"])
                if set(args) != {"code"} or not isinstance(args["code"], str):
                    raise ValueError("invalid tool arguments")
                output = sandbox.execute(workspace, client.config["docker_image"], args["code"])
            except Exception as exc:
                output = {"error": type(exc).__name__}
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(output)})
    raise RuntimeError("agent_turn_budget_exhausted")


def run_agent(payload, client, with_task_skill):
    with tempfile.TemporaryDirectory(prefix="wto-execute-") as temp:
        workspace = Path(temp)
        common_workspace(workspace)
        (workspace / "input.json").write_text(json.dumps(payload))
        system = EXECUTION_SYSTEM
        if with_task_skill:
            shutil.copyfile(ROOT / "task_skill.md", workspace / "TASK_SKILL.md")
            system += " Read and use TASK_SKILL.md."
        agent_loop(client, workspace, system, client.config["agent_turns"])
        return json.loads(sandbox.read_artifact(workspace, "result.json"))


def construct(client, dev_cases, with_skill, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    call_start = len(client.calls)
    record = {"arm": "build_with_skill" if with_skill else "build_without_skill",
              "status": "failed", "syntax_valid": False, "human_rework_count": None,
              "human_rework_minutes": None, "candidate_sha256": None, "boundary_decisions": None}
    try:
        with tempfile.TemporaryDirectory(prefix="wto-build-") as temp:
            build_workspace(temp, dev_cases, with_skill)
            prompt = BUILD_SYSTEM + (" Read and apply SKILL.md before implementation." if with_skill else "")
            record["tool_calls"] = agent_loop(client, temp, prompt, client.config["build_turns"])
            source = sandbox.read_artifact(temp, "candidate.py")
            # Hash and retain even syntactically invalid candidates; never repair here.
            (destination / "candidate.py").write_text(source)
            record["candidate_sha256"] = hashlib.sha256(source.encode()).hexdigest()
            decisions = json.loads(sandbox.read_artifact(temp, "offload_decisions.json"))
            record["boundary_decisions"] = decisions
            (destination / "offload_decisions.json").write_text(json.dumps(decisions, indent=2))
            ast.parse(source)
            record["syntax_valid"] = True
            record["status"] = "completed"
    except Exception as exc:
        record["error"] = type(exc).__name__
    record["wall_ms"] = round((time.perf_counter() - start) * 1000, 3)
    record["calls"] = client.calls[call_start:]
    costs = [c["cost_usd"] for c in record["calls"]]
    record["cost_usd"] = sum(costs) if all(c is not None for c in costs) else None
    (destination / "build.json").write_text(json.dumps(record, indent=2))
    return record


def run_candidate(payload, source, expected_hash, client):
    if hashlib.sha256(source.encode()).hexdigest() != expected_hash:
        raise RuntimeError("candidate changed after freeze")
    with tempfile.TemporaryDirectory(prefix="wto-candidate-") as temp:
        common_workspace(temp)
        (Path(temp) / "candidate.py").write_text(source)
        judge = SemanticJudge(client)
        calls = 0
        def bridge(request):
            nonlocal calls
            calls += 1
            if calls > len(payload["vendors"]) or not isinstance(request, dict) or set(request) != {"domain", "profile", "reference"}:
                raise ValueError("candidate semantic call budget/shape")
            if request["domain"] != payload["policy"]["domain"]:
                raise ValueError("candidate domain changed")
            if not any(request["profile"] in v["documents"] and request["reference"] in v["documents"] for v in payload["vendors"]):
                raise ValueError("candidate may only send its supplied evidence")
            return judge(request["domain"], request["profile"], request["reference"])
        return sandbox.execute(temp, client.config["docker_image"], "import runpy; runpy.run_path('/work/candidate.py', run_name='__main__')",
                               initial=payload, judge=bridge, timeout=180)
