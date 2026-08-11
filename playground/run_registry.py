from __future__ import annotations

import json
import os
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any


class RunRegistry:
    """Thread-safe, bounded storage for Playground run state."""

    def __init__(self, max_records: int = 200, storage_path: Path | None = None) -> None:
        if max_records < 1:
            raise ValueError("max_records 必须大于 0")
        self.max_records = max_records
        self.storage_path = storage_path
        self._runs: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._load()

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
            self._persist()

    def update(self, run_id: str, **changes: Any) -> None:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            self._runs[run_id].update(deepcopy(changes))
            self._persist()

    def append_log(self, run_id: str, message: str) -> None:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            self._runs[run_id].setdefault("logs", []).append(message)
            self._persist()

    def snapshot(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._runs.get(run_id, {}))

    def _load(self) -> None:
        if self.storage_path is None or not self.storage_path.is_file():
            return
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            records = payload.get("runs", []) if isinstance(payload, dict) else []
            loaded = {
                str(run["id"]): run
                for run in records
                if isinstance(run, dict) and str(run.get("id", ""))
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return

        recovered = False
        now = time.time()
        for run in loaded.values():
            if run.get("status") == "running":
                run.update({
                    "status": "failed",
                    "error": "Playground 在执行期间发生重启，本次任务已中断，请重新发送。",
                    "finished_at": now,
                })
                run.setdefault("logs", []).append("检测到服务重启，已将未完成任务标记为中断")
                recovered = True
        ordered = sorted(
            loaded.values(),
            key=lambda run: float(run.get("finished_at") or run.get("created_at") or 0),
            reverse=True,
        )[:self.max_records]
        self._runs = {str(run["id"]): run for run in ordered}
        if recovered or len(ordered) != len(loaded):
            self._persist()

    def _persist(self) -> None:
        if self.storage_path is None:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.storage_path.with_suffix(f"{self.storage_path.suffix}.tmp")
        payload = {"version": 1, "runs": list(self._runs.values())}
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.storage_path)

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
