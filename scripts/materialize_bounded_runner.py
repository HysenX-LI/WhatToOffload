#!/usr/bin/env python3
"""Materialize a validated standalone Python runner and generated contract tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

try:
    from .validate_implementation_capsule import load_capsule, validate_capsule
except ImportError:  # Direct script execution.
    from validate_implementation_capsule import load_capsule, validate_capsule


ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD_ROOT = ROOT / "assets" / "scaffolds" / "python-bounded-runner" / "workflow_runner"
COMPONENTS = {
    "python-decimal-contract-v1": ROOT / "assets" / "components" / "python" / "decimal_contract.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_tests(package: str, cases: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "# Generated from implementation-capsule.json. Do not edit.",
        "import unittest",
        "",
        f"from {package} import run",
        "",
        "",
        "CASES = " + repr(list(cases)),
        "",
        "",
        "class GeneratedContractTests(unittest.TestCase):",
    ]
    for index, _case in enumerate(cases):
        lines.extend(
            [
                f"    def test_case_{index + 1:03d}(self):",
                f"        case = CASES[{index}]",
                "        self.assertEqual(run(case['input']), case['expected'], case['name'])",
                "",
            ]
        )
    lines.extend(["", "if __name__ == '__main__':", "    unittest.main()", ""])
    return "\n".join(lines)


def materialize(capsule: Mapping[str, Any], destination: Path) -> Mapping[str, Any]:
    errors = validate_capsule(capsule)
    if errors:
        raise ValueError("invalid capsule:\n- " + "\n- ".join(errors))

    target = capsule["target"]
    if target["mode"] != "standalone_python_runner":
        raise ValueError("materialization supports only standalone_python_runner")
    package = target["package"]
    expected_change = f"{package}/core.py"
    if target["allowed_changes"] != [expected_change]:
        raise ValueError(f"standalone scaffold requires allowed_changes [{expected_change!r}]")
    materialized_paths = {
        f"{package}/__init__.py",
        f"{package}/__main__.py",
        f"{package}/cli.py",
        f"{package}/core.py",
        f"{package}/envelope.py",
        "tests/test_generated_contract.py",
    }
    materialized_paths.update(
        f"{package}/{COMPONENTS[component].name}"
        for component in target["components"]
    )
    missing_immutable = sorted(set(target["immutable_paths"]) - materialized_paths)
    if missing_immutable:
        raise ValueError(
            "target.immutable_paths cannot be materialized: " + ", ".join(missing_immutable)
        )

    destination = destination.resolve()
    if destination.exists():
        if not destination.is_dir():
            raise ValueError("destination exists and is not a directory")
        if any(destination.iterdir()):
            raise ValueError("destination must be empty; refusing to overwrite files")
    else:
        destination.mkdir(parents=True)

    package_dir = destination / package
    shutil.copytree(SCAFFOLD_ROOT, package_dir)
    for component in target["components"]:
        source = COMPONENTS[component]
        shutil.copy2(source, package_dir / source.name)

    tests_dir = destination / "tests"
    tests_dir.mkdir()
    generated_test = tests_dir / "test_generated_contract.py"
    generated_test.write_text(
        _render_tests(package, capsule["acceptance"]["cases"]),
        encoding="utf-8",
    )

    capsule_path = destination / "implementation-capsule.json"
    capsule_path.write_text(json.dumps(capsule, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    allowed = set(target["allowed_changes"])
    immutable_hashes = {}
    for path in sorted(item for item in destination.rglob("*") if item.is_file()):
        relative = path.relative_to(destination).as_posix()
        if relative not in allowed:
            immutable_hashes[relative] = _sha256(path)
    manifest = {
        "manifest_version": 1,
        "capsule_id": capsule["capsule_id"],
        "capsule_sha256": _sha256(capsule_path),
        "package": package,
        "allowed_changes": sorted(allowed),
        "immutable_sha256": immutable_hashes,
        "commands": capsule["acceptance"]["commands"],
        "final_command_index": capsule["acceptance"]["final_command_index"],
        "build_budget": capsule["build_budget"],
    }
    manifest_path = destination / "implementation-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capsule", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--manifest-out", type=Path, help="Write a harness-owned manifest copy outside the builder directory")
    args = parser.parse_args(argv)
    manifest_out = args.manifest_out.resolve() if args.manifest_out else None
    destination = args.destination.resolve()
    if manifest_out is not None:
        try:
            manifest_out.relative_to(destination)
        except ValueError:
            pass
        else:
            print("ERROR: --manifest-out must be outside the builder destination")
            return 1
        if manifest_out.exists() or not manifest_out.parent.is_dir():
            print("ERROR: --manifest-out must be a new file in an existing directory")
            return 1
    try:
        capsule = load_capsule(args.capsule)
        manifest = materialize(capsule, destination)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("ERROR: {}".format(exc))
        return 1
    if manifest_out is not None:
        try:
            with manifest_out.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        except OSError as exc:
            print("ERROR: cannot write --manifest-out: {}".format(exc))
            return 1
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
