import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.materialize_bounded_runner import materialize
from scripts.validate_implementation_capsule import validate_capsule
from scripts.verify_implementation_build import run_commands, verify_tree


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "assets" / "templates" / "implementation-capsule.json"


class ImplementationCapsuleTests(unittest.TestCase):
    def capsule(self):
        return json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def test_template_is_a_valid_capsule(self):
        self.assertEqual([], validate_capsule(self.capsule()))

    def test_validator_rejects_unresolved_overlap_and_unsafe_paths(self):
        capsule = self.capsule()
        capsule["unresolved"] = ["choose an executor"]
        capsule["target"]["immutable_paths"].append("workflow_runner/core.py")
        capsule["target"]["context_paths"] = ["../private"]
        errors = validate_capsule(capsule)
        self.assertTrue(any("unresolved" in error for error in errors))
        self.assertTrue(any("overlap" in error for error in errors))
        self.assertTrue(any("unsafe path" in error for error in errors))

    def test_validator_rejects_unknown_properties_and_test_budget_overflow(self):
        capsule = self.capsule()
        capsule["surprise"] = True
        capsule["acceptance"]["commands"].append(["python3", "extra-test.py"])
        capsule["build_budget"]["max_test_commands"] = 1
        errors = validate_capsule(capsule)
        self.assertTrue(any("unknown property surprise" in error for error in errors))
        self.assertTrue(any("exceeds" in error for error in errors))

    def test_standalone_package_name_must_be_importable(self):
        capsule = self.capsule()
        capsule["target"]["package"] = "class"
        errors = validate_capsule(capsule)
        self.assertTrue(any("importable Python package name" in error for error in errors))

    def test_existing_non_python_project_does_not_require_python_package_name(self):
        capsule = self.capsule()
        capsule["target"].update({
            "mode": "existing_project",
            "stack": "typescript",
            "package": None,
            "scaffold_id": None,
            "allowed_changes": ["src/workflow.ts"],
            "immutable_paths": ["package.json"],
        })
        capsule["change_plan"] = [{
            "path": "src/workflow.ts",
            "action": "modify",
            "responsibility": "Implement the frozen workflow contract.",
        }]
        self.assertEqual([], validate_capsule(capsule))

    def test_materialized_runner_passes_generated_contract_after_domain_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runner"
            manifest = materialize(self.capsule(), root)
            self.assertEqual([], verify_tree(root, manifest))

            core = root / "workflow_runner" / "core.py"
            core.write_text(
                "from .envelope import envelope\n\n"
                "def run(payload):\n"
                "    return envelope('completed', 'Processed input.', result={'value': payload.get('value')})\n",
                encoding="utf-8",
            )
            results, errors = run_commands(root, manifest)
            self.assertEqual([], errors)
            self.assertEqual(0, results[-1]["returncode"])

            cli = subprocess.run(
                [sys.executable, "-m", "workflow_runner"],
                cwd=root,
                input='{"value": NaN}',
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, cli.returncode)
            self.assertEqual("failed", json.loads(cli.stdout)["status"])

    def test_manifest_detects_immutable_mutation_and_unexpected_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runner"
            manifest = materialize(self.capsule(), root)
            (root / "workflow_runner" / "envelope.py").write_text("changed\n", encoding="utf-8")
            (root / "extra.py").write_text("pass\n", encoding="utf-8")
            errors = verify_tree(root, manifest)
            self.assertTrue(any("immutable file changed" in error for error in errors))
            self.assertTrue(any("unexpected file" in error for error in errors))

    def test_materializer_refuses_nonempty_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runner"
            root.mkdir()
            (root / "owned.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be empty"):
                materialize(self.capsule(), root)
            self.assertEqual("keep", (root / "owned.txt").read_text(encoding="utf-8"))

    def test_optional_decimal_component_rejects_huge_integer_before_string_conversion(self):
        path = ROOT / "assets" / "components" / "python" / "decimal_contract.py"
        spec = importlib.util.spec_from_file_location("decimal_contract_fixture", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertIsNone(module.parse_decimal(10**5000))
        self.assertEqual("-0.00", module.fixed_decimal(module.quantize_product(module.parse_decimal("-0"), 1)))

    def test_materializer_copies_selected_component_as_immutable(self):
        capsule = self.capsule()
        capsule["target"]["components"] = ["python-decimal-contract-v1"]
        capsule["target"]["immutable_paths"].append("workflow_runner/decimal_contract.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runner"
            manifest = materialize(capsule, root)
            self.assertTrue((root / "workflow_runner" / "decimal_contract.py").is_file())
            self.assertIn("workflow_runner/decimal_contract.py", manifest["immutable_sha256"])

    def test_external_manifest_detects_internal_manifest_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "runner"
            lock = base / "manifest.lock.json"
            created = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "materialize_bounded_runner.py"),
                    str(TEMPLATE),
                    str(root),
                    "--manifest-out",
                    str(lock),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, created.returncode, created.stdout + created.stderr)
            internal = root / "implementation-manifest.json"
            value = json.loads(internal.read_text(encoding="utf-8"))
            value["allowed_changes"] = ["workflow_runner/cli.py"]
            internal.write_text(json.dumps(value), encoding="utf-8")

            checked = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "verify_implementation_build.py"),
                    str(root),
                    "--manifest",
                    str(lock),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, checked.returncode)
            self.assertIn("internal manifest differs", checked.stdout)

            inside = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "verify_implementation_build.py"),
                    str(root),
                    "--manifest",
                    str(internal),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(1, inside.returncode)
            self.assertIn("must be outside", inside.stdout)


if __name__ == "__main__":
    unittest.main()
