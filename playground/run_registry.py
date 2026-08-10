from __future__ import annotations

import threading
from copy import deepcopy
from typing import Any


class RunRegistry:
    """Thread-safe, bounded storage for in-memory Playground run state."""

    def __init__(self, max_records: int = 200) -> None:
        if max_records < 1:
            raise ValueError("max_records 必须大于 0")
        self.max_records = max_records
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def has_active(self) -> bool:
        with self._lock:
            return any(run.get("status") == "running" for run in self._runs.values())

    def add(self, run: dict[str, Any]) -> None:
        run_id = str(run.get("id", ""))
        if not run_id:
            raise ValueError("运行记录缺少 id")
        with self._lock:
            if run_id in self._runs:
                raise ValueError(f"运行记录已存在：{run_id}")
            self._prune_completed_for_insert()
            self._runs[run_id] = deepcopy(run)

    def update(self, run_id: str, **changes: Any) -> None:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            self._runs[run_id].update(deepcopy(changes))

    def append_log(self, run_id: str, message: str) -> None:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            self._runs[run_id].setdefault("logs", []).append(message)

    def snapshot(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._runs.get(run_id, {}))

    def _prune_completed_for_insert(self) -> None:
        overflow = len(self._runs) - self.max_records + 1
        if overflow <= 0:
            return
        completed = sorted(
            (
                (run_id, float(run.get("finished_at") or run.get("created_at") or 0))
                for run_id, run in self._runs.items()
                if run.get("status") != "running"
            ),
            key=lambda item: item[1],
        )
        for run_id, _ in completed[:overflow]:
            self._runs.pop(run_id, None)
