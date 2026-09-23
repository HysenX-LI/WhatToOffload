#!/usr/bin/env python3
"""Validate a compact implementation capsule without third-party packages."""

from __future__ import annotations

import argparse
import json
import keyword
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Optional, Sequence


TOP_LEVEL_KEYS = {
    "capsule_version",
    "capsule_id",
    "source",
    "target",
    "decisions",
    "public_contract",
    "change_plan",
    "acceptance",
    "build_budget",
    "stop_conditions",
    "unresolved",
}
SOURCE_KEYS = {
    "design_id",
    "design_version",
    "input_version",
    "quality_boundary",
    "accepted_tradeoffs",
    "authorization_scope",
    "references",
}
TARGET_KEYS = {
    "mode",
    "stack",
    "package",
    "scaffold_id",
    "components",
    "context_paths",
    "allowed_changes",
    "immutable_paths",
    "dependencies",
}
KNOWN_SCAFFOLDS = {"python-bounded-runner-v1"}
KNOWN_COMPONENTS = {"python-decimal-contract-v1"}
WORKFLOW_CLASSES = {"short_lived_bounded", "durable_asynchronous"}
CAPABILITY_ROLES = {"code", "tool", "jev", "small_llm", "strong_llm_or_agent", "human"}
PATH_FIELDS = {"context_paths", "allowed_changes", "immutable_paths"}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SECRET_RE = re.compile(r"(?:Bearer\s+[A-Za-z0-9._~+/=-]{12,}|\b(?:sk|pk)-[A-Za-z0-9_-]{12,})", re.I)
PLACEHOLDER_RE = re.compile(r"(?:\bTBD\b|\bTODO\b|<[^<>]+>)", re.I)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(_nonempty(item) for item in value)
    )


def _mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _safe_relative_path(value: Any) -> bool:
    if not _nonempty(value) or "\\" in value or "://" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and "." not in path.parts and ".." not in path.parts


def _exact_keys(value: Any, expected: set[str], label: str, errors: list[str]) -> bool:
    if not _mapping(value):
        errors.append(f"{label} must be an object")
        return False
    actual = set(value)
    for missing in sorted(expected - actual):
        errors.append(f"{label} is missing {missing}")
    for extra in sorted(actual - expected):
        errors.append(f"{label} has unknown property {extra}")
    return actual == expected


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_capsule(capsule: Any) -> list[str]:
    errors: list[str] = []
    if not _exact_keys(capsule, TOP_LEVEL_KEYS, "capsule", errors):
        if not _mapping(capsule):
            return errors

    if capsule.get("capsule_version") != 1:
        errors.append("capsule_version must be 1")
    if not _nonempty(capsule.get("capsule_id")):
        errors.append("capsule_id must be a non-empty string")

    source = capsule.get("source")
    if _exact_keys(source, SOURCE_KEYS, "source", errors):
        for key in ("design_id", "design_version", "input_version", "quality_boundary"):
            if not _nonempty(source.get(key)):
                errors.append(f"source.{key} must be a non-empty string")
        if not _strings(source.get("accepted_tradeoffs")):
            errors.append("source.accepted_tradeoffs must be a string array")
        if not _strings(source.get("authorization_scope"), nonempty=True):
            errors.append("source.authorization_scope must be a non-empty string array")
        references = source.get("references")
        if not isinstance(references, list):
            errors.append("source.references must be an array")
        else:
            for index, reference in enumerate(references):
                label = f"source.references[{index}]"
                if not _exact_keys(reference, {"path", "sha256"}, label, errors):
                    continue
                if not _safe_relative_path(reference.get("path")):
                    errors.append(f"{label}.path must be a safe relative path")
                if not isinstance(reference.get("sha256"), str) or not HASH_RE.fullmatch(reference["sha256"]):
                    errors.append(f"{label}.sha256 must be 64 lowercase hexadecimal characters")

    target = capsule.get("target")
    if _exact_keys(target, TARGET_KEYS, "target", errors):
        if target.get("mode") not in {"existing_project", "standalone_python_runner"}:
            errors.append("target.mode is unsupported")
        if not _nonempty(target.get("stack")):
            errors.append("target.stack must be a non-empty string")
        package = target.get("package")
        if package is not None and not _nonempty(package):
            errors.append("target.package must be null or a non-empty string")
        scaffold_id = target.get("scaffold_id")
        if scaffold_id is not None and scaffold_id not in KNOWN_SCAFFOLDS:
            errors.append(f"target.scaffold_id is unsupported: {scaffold_id!r}")
        components = target.get("components")
        if not _strings(components):
            errors.append("target.components must be a string array")
        else:
            for component in components:
                if component not in KNOWN_COMPONENTS:
                    errors.append(f"unsupported component: {component}")
        for key in PATH_FIELDS:
            values = target.get(key)
            if not _strings(values, nonempty=(key == "allowed_changes")):
                errors.append(f"target.{key} must be a{' non-empty' if key == 'allowed_changes' else ''} string array")
                continue
            if len(values) != len(set(values)):
                errors.append(f"target.{key} must not contain duplicates")
            for value in values:
                if not _safe_relative_path(value):
                    errors.append(f"target.{key} contains unsafe path {value!r}")
        if not _strings(target.get("dependencies")):
            errors.append("target.dependencies must be a string array")
        allowed = set(target.get("allowed_changes") or [])
        immutable = set(target.get("immutable_paths") or [])
        overlap = sorted(allowed & immutable)
        if overlap:
            errors.append("target allowed_changes and immutable_paths overlap: " + ", ".join(overlap))
        if target.get("mode") == "standalone_python_runner":
            if target.get("stack") != "python_stdlib":
                errors.append("standalone_python_runner currently requires target.stack python_stdlib")
            if scaffold_id != "python-bounded-runner-v1":
                errors.append("standalone_python_runner requires scaffold python-bounded-runner-v1")
            if not isinstance(package, str) or not PACKAGE_RE.fullmatch(package) or keyword.iskeyword(package):
                errors.append("standalone_python_runner requires a lowercase, importable Python package name")

    decisions = capsule.get("decisions")
    if _exact_keys(decisions, {"workflow_class", "nodes"}, "decisions", errors):
        if decisions.get("workflow_class") not in WORKFLOW_CLASSES:
            errors.append("decisions.workflow_class is unsupported")
        nodes = decisions.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            errors.append("decisions.nodes must be a non-empty array")
        else:
            node_ids: set[str] = set()
            for index, node in enumerate(nodes):
                label = f"decisions.nodes[{index}]"
                expected = {"id", "capability_role", "implementation", "input_contract", "output_contract"}
                if not _exact_keys(node, expected, label, errors):
                    continue
                node_id = node.get("id")
                if not _nonempty(node_id):
                    errors.append(f"{label}.id must be a non-empty string")
                elif node_id in node_ids:
                    errors.append(f"duplicate node id: {node_id}")
                else:
                    node_ids.add(node_id)
                if node.get("capability_role") not in CAPABILITY_ROLES:
                    errors.append(f"{label}.capability_role is unsupported")
                if not _nonempty(node.get("implementation")):
                    errors.append(f"{label}.implementation must be a non-empty string")
                for key in ("input_contract", "output_contract"):
                    if not _mapping(node.get(key)):
                        errors.append(f"{label}.{key} must be an object")

    contract = capsule.get("public_contract")
    contract_keys = {"entrypoint", "input_schema", "output_schema", "statuses", "configuration_names"}
    if _exact_keys(contract, contract_keys, "public_contract", errors):
        if not _nonempty(contract.get("entrypoint")):
            errors.append("public_contract.entrypoint must be a non-empty string")
        for key in ("input_schema", "output_schema"):
            if not _mapping(contract.get(key)):
                errors.append(f"public_contract.{key} must be an object")
        if not _strings(contract.get("statuses"), nonempty=True):
            errors.append("public_contract.statuses must be a non-empty string array")
        if not _strings(contract.get("configuration_names")):
            errors.append("public_contract.configuration_names must be a string array")

    change_plan = capsule.get("change_plan")
    if not isinstance(change_plan, list) or not change_plan:
        errors.append("change_plan must be a non-empty array")
    else:
        allowed = set(target.get("allowed_changes") or []) if _mapping(target) else set()
        immutable = set(target.get("immutable_paths") or []) if _mapping(target) else set()
        for index, change in enumerate(change_plan):
            label = f"change_plan[{index}]"
            if not _exact_keys(change, {"path", "action", "responsibility"}, label, errors):
                continue
            path = change.get("path")
            action = change.get("action")
            if not _safe_relative_path(path):
                errors.append(f"{label}.path must be a safe relative path")
            if action not in {"create", "modify", "preserve"}:
                errors.append(f"{label}.action is unsupported")
            if not _nonempty(change.get("responsibility")):
                errors.append(f"{label}.responsibility must be non-empty")
            if action in {"create", "modify"} and path not in allowed:
                errors.append(f"{label}.path is not in target.allowed_changes")
            if action == "preserve" and path not in immutable:
                errors.append(f"{label}.path is not in target.immutable_paths")

    acceptance = capsule.get("acceptance")
    if _exact_keys(acceptance, {"cases", "commands", "final_command_index"}, "acceptance", errors):
        cases = acceptance.get("cases")
        if not isinstance(cases, list) or not cases:
            errors.append("acceptance.cases must be a non-empty array")
        else:
            names: set[str] = set()
            for index, case in enumerate(cases):
                label = f"acceptance.cases[{index}]"
                if not _exact_keys(case, {"name", "input", "expected"}, label, errors):
                    continue
                name = case.get("name")
                if not _nonempty(name):
                    errors.append(f"{label}.name must be non-empty")
                elif name in names:
                    errors.append(f"duplicate acceptance case name: {name}")
                else:
                    names.add(name)
        commands = acceptance.get("commands")
        if not isinstance(commands, list) or not commands:
            errors.append("acceptance.commands must be a non-empty array")
        else:
            for index, command in enumerate(commands):
                if not _strings(command, nonempty=True):
                    errors.append(f"acceptance.commands[{index}] must be a non-empty string array")
        final_index = acceptance.get("final_command_index")
        if not isinstance(final_index, int) or isinstance(final_index, bool):
            errors.append("acceptance.final_command_index must be an integer")
        elif isinstance(commands, list) and not 0 <= final_index < len(commands):
            errors.append("acceptance.final_command_index is out of range")

    budget = capsule.get("build_budget")
    budget_keys = {"wall_seconds", "max_tool_calls", "max_test_commands", "max_input_tokens"}
    if _exact_keys(budget, budget_keys, "build_budget", errors):
        for key in ("wall_seconds", "max_tool_calls", "max_test_commands"):
            if not _positive_int(budget.get(key)):
                errors.append(f"build_budget.{key} must be a positive integer")
        max_input = budget.get("max_input_tokens")
        if max_input is not None and not _positive_int(max_input):
            errors.append("build_budget.max_input_tokens must be null or a positive integer")
        commands = acceptance.get("commands") if _mapping(acceptance) else None
        max_tests = budget.get("max_test_commands")
        if isinstance(commands, list) and _positive_int(max_tests) and len(commands) > max_tests:
            errors.append("acceptance.commands exceeds build_budget.max_test_commands")

    if not _strings(capsule.get("stop_conditions"), nonempty=True):
        errors.append("stop_conditions must be a non-empty string array")
    if capsule.get("unresolved") != []:
        errors.append("unresolved must be an empty array before implementation")

    for path, value in _walk(capsule):
        if isinstance(value, str):
            if SECRET_RE.search(value):
                errors.append(f"{path} contains a credential-like value")
            if PLACEHOLDER_RE.search(value):
                errors.append(f"{path} contains an unresolved placeholder")

    return errors


def load_capsule(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capsule", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        capsule = load_capsule(args.capsule)
    except (OSError, json.JSONDecodeError) as exc:
        errors = [f"cannot load capsule: {exc}"]
    else:
        errors = validate_capsule(capsule)

    if args.json_output:
        print(json.dumps({"valid": not errors, "errors": errors}, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print("ERROR: " + error)
    else:
        print("implementation capsule is valid")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
