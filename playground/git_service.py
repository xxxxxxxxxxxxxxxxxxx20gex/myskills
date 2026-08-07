from __future__ import annotations

import os
import re
import subprocess
import threading
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Any, Callable


class GitOperationError(RuntimeError):
    pass


class GitService:
    def __init__(
        self,
        root: Path,
        has_active_runs: Callable[[], bool],
        proxy_host: str = "127.0.0.1",
        proxy_port: int = 0,
    ) -> None:
        self.root = root
        self.has_active_runs = has_active_runs
        self.lock = threading.Lock()
        self.proxy_host = proxy_host
        self.proxy_port = self.validate_proxy_port(proxy_port)

    @staticmethod
    def validate_proxy_port(value: Any) -> int:
        if isinstance(value, bool):
            raise ValueError("代理端口必须是 0–65535 的整数")
        try:
            port = int(value)
        except (TypeError, ValueError) as error:
            raise ValueError("代理端口必须是 0–65535 的整数") from error
        if port < 0 or port > 65535:
            raise ValueError("代理端口必须是 0–65535 的整数")
        return port

    def proxy_url(self) -> str:
        return f"http://{self.proxy_host}:{self.proxy_port}" if self.proxy_port else ""

    def set_proxy_port(self, value: Any) -> int:
        port = self.validate_proxy_port(value)
        with self.lock:
            self.proxy_port = port
        return port

    def run(self, args: list[str], *, timeout: int = 30, check: bool = True) -> str:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GCM_INTERACTIVE"] = "Never"
        command = ["git"]
        proxy = self.proxy_url()
        if proxy:
            command.extend(["-c", f"http.proxy={proxy}"])
        command.extend(args)
        process = subprocess.run(
            command,
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # Preserve leading spaces: porcelain status uses them as meaningful
        # column values (for example `` M file``).
        output = (process.stdout or "").rstrip()
        error = (process.stderr or "").rstrip()
        if check and process.returncode != 0:
            raise GitOperationError(error or output or f"Git 退出码 {process.returncode}")
        return output

    @staticmethod
    def safe_remote_url(value: str) -> str:
        try:
            parsed = urllib.parse.urlsplit(value)
            if parsed.username or parsed.password:
                host = parsed.hostname or ""
                if parsed.port:
                    host += f":{parsed.port}"
                return urllib.parse.urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))
        except ValueError:
            pass
        return value

    @staticmethod
    def path_is_safe(path: str) -> bool:
        normalized = path.replace("\\", "/").strip("/")
        pure = PurePosixPath(normalized)
        if not normalized or pure.is_absolute() or ".." in pure.parts:
            return False
        name = pure.name.lower()
        if name in {".env_example", ".env.example"}:
            return True
        blocked_parts = {".git", ".runs", ".agents", "node_modules", "playground-uploads", "__pycache__"}
        if any(part.lower() in blocked_parts for part in pure.parts):
            return False
        if name == ".env" or name.startswith(".env.") or name.startswith("secrets."):
            return False
        if name in {"credentials.toml", "auth.json"} or name.endswith((".pem", ".key", ".crt", ".p12", ".pfx")):
            return False
        return True

    def status_entries(self) -> list[dict[str, Any]]:
        text = self.run(["-c", "core.quotepath=false", "status", "--porcelain=v1", "--untracked-files=all"])
        entries: list[dict[str, Any]] = []
        for line in text.splitlines():
            if len(line) < 4:
                continue
            code = line[:2]
            raw_path = line[3:]
            original = ""
            path = raw_path
            if " -> " in raw_path:
                original, path = raw_path.split(" -> ", 1)
            entries.append({
                "status": code,
                "path": path,
                "original_path": original,
                "safe": self.path_is_safe(path) and (not original or self.path_is_safe(original)),
                "staged": code[0] not in {" ", "?"},
            })
        return entries

    def status(self) -> dict[str, Any]:
        branch = self.run(["branch", "--show-current"])
        upstream = self.run(["rev-parse", "--abbrev-ref", "@{upstream}"], check=False)
        ahead = behind = 0
        if upstream:
            counts = self.run(["rev-list", "--left-right", "--count", f"HEAD...{upstream}"], check=False)
            match = re.fullmatch(r"(\d+)\s+(\d+)", counts)
            if match:
                ahead, behind = map(int, match.groups())
        remote = self.run(["remote", "get-url", "origin"], check=False)
        helper = self.run(["config", "--get", "credential.helper"], check=False)
        entries = self.status_entries()
        return {
            "branch": branch,
            "upstream": upstream,
            "remote": self.safe_remote_url(remote),
            "ahead": ahead,
            "behind": behind,
            "files": entries,
            "dirty": bool(entries),
            "gcm_configured": "manager" in helper.lower(),
            "active_runs": self.has_active_runs(),
            "proxy_host": self.proxy_host,
            "proxy_port": self.proxy_port,
            "proxy_enabled": bool(self.proxy_port),
        }

    def diff(self, path: str) -> dict[str, str]:
        normalized = path.replace("\\", "/").strip("/")
        entries = {entry["path"]: entry for entry in self.status_entries()}
        entry = entries.get(normalized)
        if not entry or not entry["safe"]:
            raise ValueError("文件不在可预览的改动列表中")
        target = (self.root / normalized).resolve()
        if self.root not in target.parents and target != self.root:
            raise ValueError("文件路径超出仓库")
        if entry["status"] == "??":
            if not target.is_file() or target.stat().st_size > 200_000:
                return {"path": normalized, "diff": "新文件过大或不是可预览文本文件。"}
            try:
                content = target.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                content = "二进制文件，无法显示文本预览。"
            return {"path": normalized, "diff": content[:200_000]}
        unstaged = self.run(["diff", "--no-ext-diff", "--", normalized], check=False)
        staged = self.run(["diff", "--cached", "--no-ext-diff", "--", normalized], check=False)
        combined = ""
        if staged:
            combined += "# 已暂存\n" + staged
        if unstaged:
            combined += ("\n\n" if combined else "") + "# 未暂存\n" + unstaged
        return {"path": normalized, "diff": combined or "没有可显示的文本差异。"}

    def assert_writable(self) -> None:
        if self.has_active_runs():
            raise GitOperationError("有 Skill 智能体正在运行，请等待任务结束后再操作 Git")

    def fetch(self) -> dict[str, Any]:
        self.assert_writable()
        with self.lock:
            output = self.run(["fetch", "--prune", "origin"], timeout=90)
        return {"message": output or "已检查远程更新", "status": self.status()}

    def pull(self) -> dict[str, Any]:
        self.assert_writable()
        if self.status_entries():
            raise GitOperationError("工作区有未提交改动，不能自动拉取；请先提交并推送")
        with self.lock:
            output = self.run(["pull", "--ff-only"], timeout=120)
        return {"message": output or "本地代码已更新", "restart_required": True, "status": self.status()}

    def commit_and_push(self, message: str, selected_paths: Any) -> dict[str, Any]:
        self.assert_writable()
        message = message.strip()
        if not message or len(message) > 120 or "\n" in message:
            raise ValueError("提交信息长度应为 1–120 个字符且不能换行")
        if not isinstance(selected_paths, list) or not selected_paths:
            raise ValueError("请至少选择一个文件")

        entries = {entry["path"]: entry for entry in self.status_entries()}
        selected: list[dict[str, Any]] = []
        for raw_path in selected_paths:
            path = str(raw_path).replace("\\", "/").strip("/")
            entry = entries.get(path)
            if not entry or not entry["safe"]:
                raise ValueError(f"文件不可提交或状态已变化：{path}")
            selected.append(entry)

        pre_staged = [entry["path"] for entry in entries.values() if entry["staged"]]
        if pre_staged:
            raise GitOperationError("检测到外部已暂存文件，请先在终端取消暂存后再使用网页提交")

        stage_paths: list[str] = []
        for entry in selected:
            stage_paths.extend(path for path in (entry["original_path"], entry["path"]) if path)

        with self.lock:
            self.run(["add", "--", *stage_paths])
            staged = [path for path in self.run(["diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB"]).splitlines() if path]
            unsafe = [path for path in staged if not self.path_is_safe(path)]
            if unsafe:
                self.run(["restore", "--staged", "--", *stage_paths], check=False)
                raise GitOperationError("暂存区包含禁止提交的敏感或运行文件")
            if not staged:
                raise GitOperationError("选中的文件没有形成可提交改动")
            try:
                self.run(["commit", "-m", message], timeout=90)
            except Exception:
                self.run(["restore", "--staged", "--", *stage_paths], check=False)
                raise
            commit = self.run(["rev-parse", "--short", "HEAD"])
            branch = self.run(["branch", "--show-current"])
            if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
                raise GitOperationError("当前分支名称无效，无法自动推送")
            try:
                push_output = self.run(["push", "origin", branch], timeout=120)
            except Exception as error:
                raise GitOperationError(f"本地提交 {commit} 已创建，但推送失败：{error}") from error
        return {"commit": commit, "branch": branch, "message": push_output or "提交并推送成功", "status": self.status()}
