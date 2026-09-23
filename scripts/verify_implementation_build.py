#!/usr/bin/env python3
"""Verify immutable build artifacts and optionally run capsule acceptance commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Optional, Sequence


SECRET_RE = re.compile(r"(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|\b(?:sk|pk)-[A-Za-z0-9_-]{12,})", re.I)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "://" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and "." not in path.parts and ".." not in path.parts


def verify_tree(root: Path, manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    immutable = manifest.get("immutable_sha256")
    allowed = manifest.get("allowed_changes")
    if not isinstance(immutable, Mapping):
        return ["manifest immutable_sha256 must be an object"]
    if not isinstance(allowed, list) or not all(_safe_relative(item) for item in allowed):
        return ["manifest allowed_changes must contain safe relative paths"]

    expected = set(immutable) | set(allowed) | {"implementation-manifest.json"}
    for relative, digest in immutable.items():
        if not _safe_relative(relative):
            errors.append(f"unsafe immutable path: {relative!r}")
            continue
        path = root / relative
        if not path.is_file():
            errors.append(f"missing immutable file: {relative}")
            continue
        actual = _sha256(path)
        if actual != digest:
            errors.append(f"immutable file changed: {relative}")

    capsule = root / "implementation-capsule.json"
    expected_capsule_hash = manifest.get("capsule_sha256")
    if not capsule.is_file():
        errors.append("missing implementation-capsule.json")
    elif not isinstance(expected_capsule_hash, str) or _sha256(capsule) != expected_capsule_hash:
        errors.append("implementation capsule hash does not match manifest")

    for path in root.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in expected:
            errors.append(f"unexpected file outside allowed changes: {relative}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SECRET_RE.search(text):
            errors.append(f"credential-like value found in {relative}")
    return errors


def run_commands(root: Path, manifest: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[str]]:
    results = []
    errors = []
    commands = manifest.get("commands")
    budget = manifest.get("build_budget")
    if not isinstance(commands, list) or not isinstance(budget, Mapping):
        return results, ["manifest commands or build_budget is invalid"]
    timeout = budget.get("wall_seconds")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        return results, ["manifest wall_seconds is invalid"]
    started = time.monotonic()
    for index, command in enumerate(commands):
        if not isinstance(command, list) or not command or not all(isinstance(arg, str) and arg for arg in command):
            errors.append(f"command {index} is invalid")
            continue
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            errors.append("acceptance command budget exhausted")
            break
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                text=True,
                capture_output=True,
                timeout=remaining,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"command {index} could not complete: {exc}")
            break
        record = {
            "index": index,
            "command": command,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }
        results.append(record)
        if completed.returncode != 0:
            errors.append(f"command {index} failed with exit code {completed.returncode}")
            break
    return results, errors


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--manifest", type=Path, help="Harness-owned manifest copy outside the builder directory")
    parser.add_argument("--run-tests", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    internal_manifest_path = root / "implementation-manifest.json"
    manifest_path = args.manifest.resolve() if args.manifest else internal_manifest_path
    if args.manifest:
        try:
            manifest_path.relative_to(root)
        except ValueError:
            pass
        else:
            print(json.dumps({"valid": False, "errors": ["--manifest must be outside the builder root"]}, indent=2))
            return 1
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [f"cannot load manifest: {exc}"]}, indent=2))
        return 1

    errors = []
    if args.manifest:
        try:
            internal_manifest = json.loads(internal_manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"cannot load internal manifest: {exc}")
        else:
            if internal_manifest != manifest:
                errors.append("internal manifest differs from harness-owned manifest")
    errors.extend(verify_tree(root, manifest))
    command_results = []
    if args.run_tests and not errors:
        command_results, command_errors = run_commands(root, manifest)
        errors.extend(command_errors)
    result = {
        "valid": not errors,
        "errors": errors,
        "commands": command_results,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
