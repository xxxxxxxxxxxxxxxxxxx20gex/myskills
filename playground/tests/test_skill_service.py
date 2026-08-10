from __future__ import annotations

import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PLAYGROUND = Path(__file__).resolve().parents[1]
if str(PLAYGROUND) not in sys.path:
    sys.path.insert(0, str(PLAYGROUND))

from skill_service import SkillService
from rating_service import RatingService


class SkillServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for folder in ("自创skills", "已测skills", "待测skills"):
            (self.root / folder).mkdir()
        skill = self.root / "自创skills" / "sample"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: sample\ndescription: Sample skill\n---\n# Workflow\n", encoding="utf-8")
        (skill / "script.py").write_text("print('ok')\n", encoding="utf-8")
        (skill / ".env").write_text("SECRET=value\n", encoding="utf-8")

        def resolve(relative: str) -> Path:
            candidate = (self.root / relative).resolve()
            if self.root not in candidate.parents or not (candidate / "SKILL.md").is_file():
                raise ValueError("invalid skill")
            return candidate

        def read_name(skill: Path) -> str:
            for line in (skill / "SKILL.md").read_text(encoding="utf-8").splitlines():
                if line.startswith("name:"):
                    return line.split(":", 1)[1].strip()
            raise ValueError("missing name")

        self.service = SkillService(self.root, resolve, read_name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_list_tree_preview_and_export_hide_secret(self) -> None:
        listed = self.service.list_skills()["skills"]
        self.assertEqual(listed[0]["path"], "自创skills/sample")
        tree = self.service.tree("自创skills/sample")["entries"]
        env = next(item for item in tree if item["path"] == ".env")
        self.assertFalse(env["readable"])
        with self.assertRaisesRegex(ValueError, "敏感凭据"):
            self.service.read_file("自创skills/sample", ".env")
        _, data, excluded = self.service.export_zip("自创skills/sample")
        self.assertIn(".env", excluded)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertNotIn("sample/.env", archive.namelist())
            self.assertIn("sample/SKILL.md", archive.namelist())

    def test_import_and_recoverable_delete(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("new-skill/SKILL.md", "---\nname: new-skill\ndescription: New\n---\n# Use\n")
            archive.writestr("new-skill/readme.md", "hello")
        imported = self.service.import_zip(buffer.getvalue(), "tested", "development")
        self.assertEqual(imported["path"], "已测skills/new-skill")
        listed = {item["path"]: item for item in self.service.list_skills()["skills"]}
        self.assertEqual(listed["已测skills/new-skill"]["category"], "development")
        ratings = RatingService(self.root, ("自创skills", "已测skills", "待测skills"))
        ratings.update_skill("已测skills/new-skill", "A", "keep me")
        moved = self.service.move("已测skills/new-skill", "pending")
        ratings.move_skill(moved["old_path"], moved["new_path"])
        self.assertEqual(moved["new_path"], "待测skills/new-skill")
        listed = {item["path"]: item for item in self.service.list_skills()["skills"]}
        self.assertEqual(listed["待测skills/new-skill"]["category"], "development")
        self.assertEqual(ratings.load()["skills"]["待测skills/new-skill"]["note"], "keep me")
        deleted = self.service.delete("待测skills/new-skill", "待测skills/new-skill")
        self.assertFalse((self.root / "待测skills" / "new-skill").exists())
        self.assertTrue((self.root / deleted["trash"]).exists())

    def test_import_rejects_secrets_and_parent_paths(self) -> None:
        for filename in ("bad/.env", "../SKILL.md"):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("bad/SKILL.md", "---\nname: bad\n---\n")
                archive.writestr(filename, "secret")
            with self.assertRaises(ValueError):
                self.service.import_zip(buffer.getvalue(), "pending", "system")


if __name__ == "__main__":
    unittest.main()
