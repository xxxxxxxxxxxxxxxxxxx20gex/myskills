from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

PLAYGROUND = Path(__file__).resolve().parents[1]
if str(PLAYGROUND) not in sys.path:
    sys.path.insert(0, str(PLAYGROUND))

from server import RUNS_ROOT, resolve_workspace_file


class WorkspaceFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run_id = "workspace-file-test"
        self.workspace = RUNS_ROOT / self.run_id / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(RUNS_ROOT / self.run_id, ignore_errors=True)

    def test_allows_file_from_matching_run_workspace(self) -> None:
        target = self.workspace / "preview.txt"
        target.write_text("preview", encoding="utf-8")
        self.assertEqual(resolve_workspace_file(self.run_id, str(target)), target.resolve())

    def test_blocks_sensitive_and_outside_files(self) -> None:
        secret = self.workspace / ".env"
        secret.write_text("secret", encoding="utf-8")
        with self.assertRaises(ValueError):
            resolve_workspace_file(self.run_id, str(secret))
        with self.assertRaises(ValueError):
            resolve_workspace_file(self.run_id, str(Path.home() / "outside.txt"))

    def test_blocks_another_runs_workspace(self) -> None:
        other = RUNS_ROOT / "another-run" / "workspace" / "file.txt"
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_text("other", encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                resolve_workspace_file(self.run_id, str(other))
        finally:
            shutil.rmtree(RUNS_ROOT / "another-run", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
