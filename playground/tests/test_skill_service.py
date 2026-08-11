from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml


PLAYGROUND = Path(__file__).resolve().parents[1]
if str(PLAYGROUND) not in sys.path:
    sys.path.insert(0, str(PLAYGROUND))

from skill_service import SkillService


class SkillServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for folder in ("自创skills", "已测skills", "待测skills"):
            (self.root / folder).mkdir()
        self.skill = self.root / "自创skills" / "sample"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text(
            "---\nname: sample\ndescription: Sample skill\n---\n# Workflow\n",
            encoding="utf-8",
        )
        (self.skill / "script.py").write_text("print('ok')\n", encoding="utf-8")
        (self.skill / ".env").write_text("SECRET=value\n", encoding="utf-8")
        (self.skill / "private.pem").write_text("PRIVATE\n", encoding="utf-8")

        def resolve(relative: str) -> Path:
            candidate = (self.root / relative).resolve()
            if self.root not in candidate.parents or not (candidate / "SKILL.md").is_file():
                raise ValueError("invalid skill")
            return candidate

        self.service = SkillService(self.root, resolve)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_list_skills_reads_frontmatter_and_saved_metadata(self) -> None:
        self.service.metadata_path.write_text(
            yaml.safe_dump({
                "version": 1,
                "skills": {"自创skills/sample": {"category": "system", "analysis": {"final_results": ["done"]}}},
            }, allow_unicode=True),
            encoding="utf-8",
        )
        listed = self.service.list_skills()["skills"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["path"], "自创skills/sample")
        self.assertEqual(listed[0]["summary"], "Sample skill")
        self.assertEqual(listed[0]["headings"], ["Workflow"])
        self.assertEqual(listed[0]["category"], "system")
        self.assertEqual(listed[0]["analysis"]["final_results"], ["done"])

    def test_analysis_source_excludes_credentials(self) -> None:
        source = self.service.analysis_source("自创skills/sample")
        self.assertIn("SKILL.md", source)
        self.assertIn("script.py", source)
        self.assertNotIn("SECRET=value", source)
        self.assertNotIn("PRIVATE", source)

    def test_save_analysis_preserves_category(self) -> None:
        self.service.metadata_path.write_text(
            "version: 1\nskills:\n  自创skills/sample:\n    category: system\n",
            encoding="utf-8",
        )
        saved = self.service.save_analysis("自创skills/sample", {"final_results": ["done"]}, "test-model")
        self.assertEqual(saved["model"], "test-model")
        payload = yaml.safe_load(self.service.metadata_path.read_text(encoding="utf-8"))
        entry = payload["skills"]["自创skills/sample"]
        self.assertEqual(entry["category"], "system")
        self.assertEqual(entry["analysis"]["final_results"], ["done"])


if __name__ == "__main__":
    unittest.main()
