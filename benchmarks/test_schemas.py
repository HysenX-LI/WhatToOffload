import json
import re
import unittest
from pathlib import Path
from urllib.parse import unquote

from scripts.validate_audit_log import EVENT_TYPES, PRIVACY_LEVELS, REASON_CODES, STAGES


ROOT = Path(__file__).resolve().parents[1]


class SchemaFilesTests(unittest.TestCase):
    def test_formal_schemas_are_valid_json_and_identify_drafts(self):
        names = (
            "workflow-audit-event.schema.json",
            "gap-attribution.schema.json",
            "frozen-field-reference.schema.json",
            "implementation-capsule.schema.json",
        )
        for name in names:
            with self.subTest(name=name):
                value = json.loads((ROOT / "assets" / "schemas" / name).read_text(encoding="utf-8"))
                self.assertEqual("https://json-schema.org/draft/2020-12/schema", value["$schema"])
                self.assertEqual("object", value["type"])

    def test_schema_and_validator_vocabularies_match(self):
        audit = json.loads((ROOT / "assets" / "schemas" / "workflow-audit-event.schema.json").read_text(encoding="utf-8"))
        properties = audit["properties"]
        self.assertEqual(STAGES, set(properties["stage"]["enum"]))
        self.assertEqual(EVENT_TYPES, set(properties["event_type"]["enum"]))
        self.assertEqual(PRIVACY_LEVELS, set(properties["privacy"]["enum"]))
        self.assertEqual(REASON_CODES, set(audit["$defs"]["reasonCode"]["enum"]))

        gap = json.loads((ROOT / "assets" / "schemas" / "gap-attribution.schema.json").read_text(encoding="utf-8"))
        gap_causes = set(gap["properties"]["gaps"]["items"]["properties"]["primary_cause"]["enum"])
        self.assertEqual(REASON_CODES - {"above_threshold"}, gap_causes)

    def test_repository_json_files_parse(self):
        for path in ROOT.rglob("*.json"):
            if ".local" in path.parts:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_local_markdown_links_resolve(self):
        pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        missing = []
        for path in ROOT.rglob("*.md"):
            if ".local" in path.parts:
                continue
            for target in pattern.findall(path.read_text(encoding="utf-8")):
                target = target.strip().strip("<>").split("#", 1)[0]
                if not target or "://" in target or target.startswith(("mailto:", "#")):
                    continue
                resolved = (path.parent / unquote(target)).resolve()
                if not resolved.exists():
                    missing.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
