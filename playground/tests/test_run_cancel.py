from __future__ import annotations

import subprocess
import sys
import time
import unittest
from pathlib import Path


PLAYGROUND = Path(__file__).resolve().parents[1]
if str(PLAYGROUND) not in sys.path:
    sys.path.insert(0, str(PLAYGROUND))

import server
from run_registry import RunRegistry


class RunCancellationTests(unittest.TestCase):
    def test_cancel_stops_registered_process_and_marks_request(self) -> None:
        original_registry = server.RUNS
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        run_id = "abcdef123456"
        try:
            server.RUNS = RunRegistry()
            server.RUNS.add({
                "id": run_id,
                "status": "running",
                "logs": [],
                "created_at": time.time(),
            })
            with server.RUN_PROCESSES_LOCK:
                server.RUN_PROCESSES[run_id] = process

            response = server.cancel_run(run_id)
            process.wait(timeout=10)
            server.finish_canceled_run(run_id)

            run = server.RUNS.snapshot(run_id)
            self.assertEqual(response["status"], "canceling")
            self.assertTrue(run["cancel_requested"])
            self.assertEqual(run["status"], "canceled")
            self.assertIn("用户停止", "\n".join(run["logs"]))
        finally:
            with server.RUN_PROCESSES_LOCK:
                server.RUN_PROCESSES.pop(run_id, None)
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            server.RUNS = original_registry


if __name__ == "__main__":
    unittest.main()
