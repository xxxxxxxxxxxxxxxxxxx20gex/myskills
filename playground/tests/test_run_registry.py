from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from playground.run_registry import RunRegistry


def make_run(run_id: str, status: str = "completed", timestamp: float = 1) -> dict:
    return {
        "id": run_id,
        "status": status,
        "logs": [],
        "artifacts": [],
        "created_at": timestamp,
        "finished_at": timestamp if status != "running" else None,
    }


class RunRegistryTests(unittest.TestCase):
    def test_snapshot_does_not_share_mutable_state(self) -> None:
        registry = RunRegistry()
        registry.add(make_run("one"))
        registry.append_log("one", "first")

        snapshot = registry.snapshot("one")
        snapshot["logs"].append("not stored")

        self.assertEqual(registry.snapshot("one")["logs"], ["first"])

    def test_oldest_completed_run_is_pruned(self) -> None:
        registry = RunRegistry(max_records=2)
        registry.add(make_run("old", timestamp=1))
        registry.add(make_run("new", timestamp=2))
        registry.add(make_run("latest", timestamp=3))

        self.assertEqual(registry.snapshot("old"), {})
        self.assertEqual(registry.snapshot("new")["id"], "new")
        self.assertEqual(registry.snapshot("latest")["id"], "latest")

    def test_running_records_are_not_pruned(self) -> None:
        registry = RunRegistry(max_records=1)
        registry.add(make_run("active", status="running"))
        registry.add(make_run("second", status="running"))

        self.assertTrue(registry.has_active())
        self.assertEqual(registry.snapshot("active")["status"], "running")
        self.assertEqual(registry.snapshot("second")["status"], "running")

    def test_completed_records_survive_restart(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            registry = RunRegistry(storage_path=path)
            registry.add(make_run("completed"))
            registry.append_log("completed", "done")

            restored = RunRegistry(storage_path=path).snapshot("completed")

            self.assertEqual(restored["status"], "completed")
            self.assertEqual(restored["logs"], ["done"])

    def test_running_record_is_marked_interrupted_after_restart(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            registry = RunRegistry(storage_path=path)
            registry.add(make_run("active", status="running"))

            restored = RunRegistry(storage_path=path).snapshot("active")

            self.assertEqual(restored["status"], "failed")
            self.assertIn("重启", restored["error"])
            self.assertTrue(restored["finished_at"])


if __name__ == "__main__":
    unittest.main()
