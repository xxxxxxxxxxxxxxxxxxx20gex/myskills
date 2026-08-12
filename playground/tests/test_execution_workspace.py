from __future__ import annotations

import sys
import unittest
from pathlib import Path

PLAYGROUND = Path(__file__).resolve().parents[1]
if str(PLAYGROUND) not in sys.path:
    sys.path.insert(0, str(PLAYGROUND))

from server import uses_project_workspace


class ExecutionWorkspaceTests(unittest.TestCase):
    def test_only_management_skill_uses_project_workspace(self) -> None:
        self.assertTrue(uses_project_workspace("自创skills/manage-myskills", "manage-myskills"))
        self.assertTrue(uses_project_workspace("自创skills/manage-myskills", "other-name"))
        self.assertFalse(uses_project_workspace("自创skills/gpt-image", "gpt-image"))


if __name__ == "__main__":
    unittest.main()
