"""ChatGPT-only Codex subprocesses and enforced workspace-only script execution."""
import json
import hashlib
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


class StopRun(RuntimeError):
    pass


def environment():
    # No provider keys, inherited agent metadata, Python paths or model endpoints.
    result = {k: os.environ[k] for k in ("HOME", "USER", "LOGNAME", "TMPDIR", "LANG", "CODEX_HOME") if k in os.environ}
    result["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    return result


def policy(workspace):
    rules = {":minimal": "read", str(Path(sys.executable).resolve().parent): "read",
             str(Path(sys.base_prefix).resolve()): "read", str(Path(workspace).resolve()): "write"}
    if sys.platform == "darwin":
        rules["/Library/Developer/CommandLineTools"] = "read"
    return ["-c", 'default_permissions="wto"', "-c", "permissions.wto.filesystem=" +
            "{" + ",".join(json.dumps(k) + "=" + json.dumps(v) for k, v in rules.items()) + "}",
            "-c", "permissions.wto.network.enabled=false"]


def script_command(cli, workspace, code):
    workspace = Path(workspace).resolve()
    return [cli, "sandbox", "-P", "wto", *policy(workspace), "-C", str(workspace), "--", sys.executable,
            "-I", "-u", "-c", "import sys; sys.path.insert(0, " + repr(str(workspace)) + ");\n" + code]


def kill(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def read_artifact(workspace, name):
    base = Path(workspace).resolve()
    path = base / name
    if path.is_symlink() or not path.resolve().is_relative_to(base) or not path.is_file() or path.stat().st_size > 100000:
        raise ValueError("missing_unsafe_or_oversized_artifact:" + name)
    return path.read_text()


def isolated_script(cli, workspace, code, initial=None, judge=None, timeout=30):
    process = subprocess.Popen(script_command(cli, workspace, code), cwd=workspace, env=environment(),
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    selector = selectors.DefaultSelector()
    for stream, kind in ((process.stdout, "out"), (process.stderr, "err")):
        selector.register(stream, selectors.EVENT_READ, kind)
    buffers = {"out": b"", "err": b""}
    final, total = None, 0
    deadline = time.monotonic() + timeout
    try:
        if initial is not None:
            process.stdin.write((json.dumps(initial) + "\n").encode()); process.stdin.flush()
        else:
            process.stdin.close()
        while selector.get_map():
            if time.monotonic() > deadline:
                raise StopRun("candidate_timeout")
            for key, _ in selector.select(0.1):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    selector.unregister(key.fileobj); continue
                total += len(chunk)
                if total > 100000:
                    raise StopRun("script_output_limit")
                buffers[key.data] += chunk
                if judge and key.data == "out":
                    while b"\n" in buffers["out"]:
                        line, buffers["out"] = buffers["out"].split(b"\n", 1)
                        value = json.loads(line)
                        if isinstance(value, dict) and set(value) == {"semantic_request"}:
                            try:
                                reply = {"answer": judge(value["semantic_request"])}
                            except StopRun:
                                raise
                            except Exception:
                                reply = {"error": "semantic_request_failed"}
                            process.stdin.write((json.dumps(reply) + "\n").encode()); process.stdin.flush()
                        elif final is None:
                            final = value
                        else:
                            raise ValueError("multiple_final_outputs")
        status = process.wait(timeout=2)
        if judge:
            if status or final is None or buffers["out"].strip():
                raise RuntimeError("candidate_process_failed:" + buffers["err"].decode(errors="replace")[-1000:])
            return final
        return {"returncode": status, "stdout": buffers["out"].decode(errors="replace"), "stderr": buffers["err"].decode(errors="replace")}
    finally:
        selector.close(); kill(process)
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()


def preflight(config):
    cli = config["cli"]
    login = subprocess.run([cli, "login", "status"], env=environment(), text=True, capture_output=True, timeout=15)
    if login.returncode or "Logged in using ChatGPT" not in login.stdout + login.stderr:
        raise StopRun("ChatGPT_login_required_no_API_fallback")
    version = subprocess.run([cli, "--version"], env=environment(), text=True, capture_output=True, timeout=15).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="wto-isolation-") as temp, tempfile.TemporaryDirectory(prefix="wto-forbidden-") as outside:
        forbidden = Path(outside) / "canary.txt"
        forbidden.write_text("not-executor-material")
        Path(temp, "alias.txt").symlink_to(forbidden)
        code = '''import json, pathlib, socket
checks={}
pathlib.Path('allowed.txt').write_text('ok')
checks['workspace_write']=pathlib.Path('allowed.txt').read_text()=='ok'
for label,path in PATHS.items():
 try: pathlib.Path(path).read_bytes(); checks[label]=False
 except PermissionError: checks[label]=True
 except Exception: checks[label]=False
try:
 s=socket.socket(); s.connect(('127.0.0.1',9)); checks['network_denied']=False
except PermissionError: checks['network_denied']=True
except Exception: checks['network_denied']=False
print(json.dumps(checks))
'''
        paths = {"repo_denied": str(REPO / "benchmarks/public_v1/data/dev/gold.json"),
                 "sibling_denied": str(forbidden), "symlink_denied": str(Path(temp, "alias.txt")),
                 "auth_denied": str(Path.home() / ".codex/auth.json")}
        probe = isolated_script(cli, temp, "PATHS=" + repr(paths) + "\n" + code)
        try:
            checks = json.loads(probe["stdout"])
        except ValueError:
            raise StopRun("isolation_probe_failed:" + probe["stderr"][-1500:])
        if probe["returncode"] or not all(checks.values()):
            raise StopRun("isolation_probe_failed:" + json.dumps(checks))
    return {"cli_version": version, "authentication": "ChatGPT", "isolation_checks": checks}


def validate_config(config):
    allowed = set(json.loads((ROOT / "config.json").read_text()))
    if set(config) != allowed or config["model"] != "gpt-5.6-sol" or config["reasoning_effort"] != "high":
        raise ValueError("Codex-only config keys and gpt-5.6-sol/high are required")
    for key in allowed - {"cli", "model", "reasoning_effort"}:
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError("positive integer limit required:" + key)
    return config


def exec_command(config, workspace, response):
    workspace = Path(workspace).resolve()
    args = [config["cli"], "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
            "--json", "--color", "never", "-C", str(workspace), "-o", str(response), "-m", config["model"], *policy(workspace)]
    overrides = {
        "model_reasoning_effort": config["reasoning_effort"], "forced_login_method": "chatgpt", "model_provider": "openai",
        "approval_policy": "never", "project_doc_max_bytes": 0, "history.persistence": "none", "web_search": "disabled",
        "shell_environment_policy.inherit": "none", "shell_environment_policy.set": {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        "features.skip_host_skill_discovery": True, "features.plugins": False, "features.apps": False,
        "features.hooks": False, "features.memories": False, "features.multi_agent": False,
        "features.browser_use": False, "features.computer_use": False, "features.image_generation": False,
        "features.shell_snapshot": False, "features.unbounded_connection_retries": False,
    }
    for k, v in overrides.items():
        val = ('{PATH="/usr/bin:/bin:/usr/sbin:/sbin"}' if isinstance(v, dict) else json.dumps(v))
        args += ["-c", k + "=" + val]
    return args + ["-"]


TOOL_TYPES = {"command_execution", "mcp_tool_call", "web_search", "file_change", "collab_tool_call", "dynamic_tool_call", "todo_list"}


def failure_kind(event):
    message = json.dumps(event).lower()
    if any(word in message for word in ("quota", "usage limit", "rate limit", "429", "credits exhausted")):
        return "Codex_quota_exhausted"
    if any(word in message for word in ("tls", "disconnected", "reconnecting", "connection", "network")):
        return "Codex_transport_failure"
    return "Codex_turn_failure"


def event_metrics(events):
    tools = {e["item"].get("id", str(i)) for i, e in enumerate(events)
             if e.get("type") in ("item.started", "item.completed") and e.get("item", {}).get("type") in TOOL_TYPES}
    usage = [e["usage"] for e in events if e.get("type") == "turn.completed" and isinstance(e.get("usage"), dict)]
    tokens = {key: (sum(u[key] for u in usage) if usage and all(type(u.get(key)) is int for u in usage) else None)
              for key in ("input_tokens", "cached_input_tokens", "output_tokens")}
    return dict(tokens, tool_calls=len(tools), reported_turns=len(usage))


class CodexClient:
    def __init__(self, config, directory):
        self.config = validate_config(config)
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.calls = []
        self.deadline = time.monotonic() + config["total_timeout_seconds"]
        self.stop_reason = None

    def check(self):
        if not self.stop_reason and len(self.calls) >= self.config["max_calls"]:
            self.stop_reason = "Codex_call_cap"
        if not self.stop_reason and time.monotonic() >= self.deadline:
            self.stop_reason = "run_timeout"
        if self.stop_reason:
            raise StopRun(self.stop_reason)

    def complete(self, workspace, prompt, kind):
        self.check()
        call = {"call_id": len(self.calls)+1, "kind": kind, "status": "started", "cost_usd": None,
                "model": self.config["model"], "reasoning_effort": self.config["reasoning_effort"], "error": None,
                "input_tokens": None, "cached_input_tokens": None, "output_tokens": None, "tool_calls": 0,
                "transport_reconnections": 0}
        self.calls.append(call)  # reserve even if spawn fails
        prefix = self.directory / ("call-%03d" % call["call_id"])
        response = prefix.with_suffix(".response.txt")
        events, process = [], None
        start = time.perf_counter()
        buffers = {"out": b"", "err": b""}
        timeout = min(self.config[kind + "_timeout_seconds"], self.deadline-time.monotonic())
        command = exec_command(self.config, workspace, response)
        prefix.with_suffix(".request.json").write_text(json.dumps({"prompt": prompt, "command": command}, indent=2))
        selector = selectors.DefaultSelector()
        try:
            process = subprocess.Popen(command, cwd=workspace, env=environment(), stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            process.stdin.write(prompt.encode()); process.stdin.close()
            for stream, label in ((process.stdout, "out"), (process.stderr, "err")):
                selector.register(stream, selectors.EVENT_READ, label)
            with prefix.with_suffix(".events.jsonl").open("wb") as log:
                while selector.get_map():
                    if time.perf_counter()-start > timeout:
                        raise StopRun("Codex_" + kind + "_timeout")
                    for key, _ in selector.select(0.1):
                        chunk = os.read(key.fileobj.fileno(), 8192)
                        if not chunk:
                            selector.unregister(key.fileobj); continue
                        buffers[key.data] += chunk
                        if len(buffers[key.data]) > 2_000_000:
                            raise StopRun("Codex_output_limit")
                        if key.data == "out":
                            log.write(chunk); log.flush()
                            while b"\n" in buffers["out"]:
                                line, buffers["out"] = buffers["out"].split(b"\n", 1)
                                try: event = json.loads(line)
                                except ValueError: continue
                                events.append(event)
                                if event_metrics(events)["tool_calls"] > self.config["max_tools_per_call"]:
                                    raise StopRun("Codex_tool_cap")
                                if event.get("type") in ("error", "turn.failed"):
                                    # The CLI emits recoverable reconnect notices as `error` items.
                                    # Allow its own bounded recovery within the same wall-clock cap.
                                    # Quota or terminal failures still stop the entire study.
                                    if event.get("type") == "error" and str(event.get("message", "")).startswith("Reconnecting...") and failure_kind(event) == "Codex_transport_failure":
                                        call["transport_reconnections"] += 1
                                        continue
                                    raise StopRun(failure_kind(event))
            call["returncode"] = process.wait(timeout=5)
            if call["returncode"] or not any(e.get("type") == "turn.completed" for e in events):
                raise StopRun("Codex_incomplete_process")
            if not response.is_file():
                raise StopRun("Codex_missing_last_message")
            call["status"] = "completed"
            return response.read_text()
        except StopRun as exc:
            self.stop_reason = str(exc); call["error"] = str(exc); call["status"] = "failed"
            raise
        except KeyboardInterrupt as exc:
            self.stop_reason = "operator_interrupt"; call["error"] = self.stop_reason; call["status"] = "failed"
            raise StopRun(self.stop_reason) from exc
        except Exception as exc:
            self.stop_reason = "Codex_process_failure"; call["error"] = type(exc).__name__; call["status"] = "failed"
            raise StopRun(self.stop_reason) from exc
        finally:
            selector.close()
            if process:
                kill(process)
                call["returncode"] = process.returncode
                process.stdout.close(); process.stderr.close()
            call.update(event_metrics(events))
            thread_ids = [e["thread_id"] for e in events if e.get("type") == "thread.started" and e.get("thread_id")]
            call["context_ids_sha256"] = [hashlib.sha256(v.encode()).hexdigest() for v in thread_ids]
            call["wall_ms"] = round((time.perf_counter()-start)*1000, 3)
            # Keep partial deliverables too; timeouts must not erase completed work.
            for name in ("result.json", "candidate.py", "offload_decisions.json"):
                try:
                    content = read_artifact(workspace, name)
                except (ValueError, OSError):
                    continue
                target = self.directory / (prefix.name + ".artifacts")
                target.mkdir(exist_ok=True)
                (target / name).write_text(content)
            prefix.with_suffix(".stderr.txt").write_bytes(buffers["err"])
            prefix.with_suffix(".metrics.json").write_text(json.dumps(call, indent=2))
            (self.directory / "calls.json").write_text(json.dumps({"calls": self.calls, "stop_reason": self.stop_reason}, indent=2))
