"""Docker-only execution of model-authored Python. No host-code fallback."""
import json
import os
import selectors
import shutil
import subprocess
import time
import uuid
from pathlib import Path


def preflight(image):
    if not shutil.which("docker"):
        raise RuntimeError("Docker is required for isolated agent/build experiments; no host fallback")
    result = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image], capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError("Docker daemon/image unavailable; prepare the configured Python image separately")
    return result.stdout.strip()


def command(workspace, image, name, code):
    return ["docker", "run", "--rm", "--pull=never", "--name", name, "-i",
            "--network=none", "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--memory=256m", "--cpus=1", "--pids-limit=32", "--user", "{}:{}".format(os.getuid(), os.getgid()),
            "--tmpfs", "/tmp:rw,noexec,size=16m", "--mount", "type=bind,src={},dst=/work".format(Path(workspace).resolve()),
            "--workdir", "/work", image, "python", "-I", "-u", "-c", "import sys; sys.path.insert(0, '/work');\n" + code]


def execute(workspace, image, code, initial=None, judge=None, timeout=30):
    name = "wto-" + uuid.uuid4().hex
    process = subprocess.Popen(command(workspace, image, name, code), stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    start = time.monotonic()
    buffers = {"stdout": b"", "stderr": b""}
    total = 0
    final = None
    try:
        if initial is not None:
            process.stdin.write((json.dumps(initial) + "\n").encode())
            process.stdin.flush()
        elif judge is None:
            process.stdin.close()
        while selector.get_map():
            if time.monotonic() - start > timeout:
                raise RuntimeError("sandbox_timeout")
            for key, _ in selector.select(timeout=0.1):
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                total += len(chunk)
                if total > 65536:
                    raise RuntimeError("sandbox_output_limit")
                kind = key.data
                buffers[kind] += chunk
                if judge is not None and kind == "stdout":
                    while b"\n" in buffers[kind]:
                        line, buffers[kind] = buffers[kind].split(b"\n", 1)
                        value = json.loads(line)
                        if isinstance(value, dict) and set(value) == {"semantic_request"}:
                            try:
                                answer = judge(value["semantic_request"])
                                reply = {"answer": answer}
                            except Exception:
                                reply = {"error": "semantic_request_failed"}
                            process.stdin.write((json.dumps(reply) + "\n").encode())
                            process.stdin.flush()
                        else:
                            if final is not None:
                                raise RuntimeError("multiple_final_outputs")
                            final = value
        code_status = process.wait(timeout=2)
        if judge is not None:
            if code_status != 0 or final is None or buffers["stdout"].strip():
                raise RuntimeError("candidate_process_failed")
            return final
        return {"exit_code": code_status, "stdout": buffers["stdout"].decode(errors="replace")[:12000],
                "stderr": buffers["stderr"].decode(errors="replace")[:4000]}
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        # A killed docker client can otherwise leave a running container.
        subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        for stream in (process.stdin, process.stdout, process.stderr):
            if not stream.closed:
                stream.close()


def read_artifact(workspace, name):
    root = Path(workspace).resolve()
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file() or path.stat().st_size > 100000:
        raise ValueError("missing/unsafe/oversized artifact: " + name)
    return path.read_text(encoding="utf-8")
