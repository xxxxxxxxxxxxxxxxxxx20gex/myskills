from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import time
import traceback
import urllib.parse
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml

from generate_project_status import update_project_status
from git_service import GitOperationError, GitService
from rating_service import RatingService


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"
ENV_PATH = ROOT / ".env"
SKILL_FOLDERS = ("自创skills", "已测skills", "待测skills")
RUNS: dict[str, dict[str, Any]] = {}
RUN_LOCK = threading.Lock()
PROJECT_SKILLS_ROOT = ROOT / ".agents" / "skills"


def has_active_runs() -> bool:
    with RUN_LOCK:
        return any(run.get("status") == "running" for run in RUNS.values())


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


CONFIG = load_config()
CONFIG_LOCK = threading.Lock()
LOCAL_ENV = load_env(ENV_PATH)
RUNS_ROOT = (ROOT / CONFIG["runs"]["directory"]).resolve()
RUNS_ROOT.mkdir(parents=True, exist_ok=True)
RATINGS = RatingService(ROOT, SKILL_FOLDERS)
GIT_CONFIG = CONFIG.get("git", {})
GIT = GitService(
    ROOT,
    has_active_runs,
    str(GIT_CONFIG.get("proxy_host", "127.0.0.1")),
    int(GIT_CONFIG.get("proxy_port", 0)),
)


def save_git_proxy_port(value: Any) -> dict[str, Any]:
    port = GIT.validate_proxy_port(value)
    with CONFIG_LOCK:
        text = CONFIG_PATH.read_text(encoding="utf-8")
        pattern = re.compile(r"(?m)^([ \t]*proxy_port:[ \t]*)\d+([ \t]*)$")
        if not pattern.search(text):
            raise RuntimeError("config.yaml 缺少 git.proxy_port 配置")
        updated = pattern.sub(lambda match: f"{match.group(1)}{port}{match.group(2)}", text, count=1)
        temporary = CONFIG_PATH.with_suffix(".yaml.tmp")
        temporary.write_text(updated, encoding="utf-8")
        os.replace(temporary, CONFIG_PATH)
        CONFIG.setdefault("git", {})["proxy_port"] = port
        GIT.set_proxy_port(port)
    return GIT.status()


def find_codex_cli() -> Path | None:
    configured = str(CONFIG.get("codex_cli", {}).get("path", "auto")).strip()
    candidates: list[Path] = []
    if configured and configured.lower() != "auto":
        candidates.append(Path(os.path.expandvars(configured)).expanduser())

    local_app_data_value = os.environ.get("LOCALAPPDATA")
    if local_app_data_value:
        local_app_data = Path(local_app_data_value)
        candidates.extend(
            sorted(
                (local_app_data / "OpenAI" / "Codex" / "bin").glob("*/codex.exe"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        )

    user_profile_value = os.environ.get("USERPROFILE")
    if user_profile_value:
        user_profile = Path(user_profile_value)
        candidates.extend(
            sorted(
                (user_profile / ".vscode" / "extensions").glob("openai.chatgpt-*/bin/windows-*/codex.exe"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
        )

    discovered = shutil.which("codex")
    if discovered:
        candidates.append(Path(discovered))

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            return candidate.resolve()
    return None


CODEX_CLI = find_codex_cli()


def secret_values() -> list[str]:
    markers = ("apikey", "api_key", "token", "password", "secret")
    return [value for key, value in LOCAL_ENV.items() if value and any(marker in key.lower() for marker in markers)]


def redact(value: str) -> str:
    result = value
    for secret in secret_values():
        result = result.replace(secret, "[REDACTED]")
    return result


def build_process_env() -> dict[str, str]:
    process_env = os.environ.copy()
    process_env.update(LOCAL_ENV)
    if LOCAL_ENV.get("baseurl"):
        process_env["OPENAI_BASE_URL"] = LOCAL_ENV["baseurl"]
    if LOCAL_ENV.get("apikey"):
        process_env["OPENAI_API_KEY"] = LOCAL_ENV["apikey"]
    return process_env


def safe_relative(base: Path, relative: str, *, must_exist: bool = False) -> Path:
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("路径超出了允许目录")
    if must_exist and not candidate.exists():
        raise FileNotFoundError(relative)
    return candidate


def resolve_skill(relative: str) -> Path:
    normalized = relative.replace("\\", "/").strip("/")
    if not any(normalized.startswith(f"{folder}/") for folder in SKILL_FOLDERS):
        raise ValueError("Skill 必须位于仓库的分类目录中")
    skill = safe_relative(ROOT, normalized, must_exist=True)
    if not (skill / "SKILL.md").is_file():
        raise ValueError("所选目录不是有效 Skill")
    return skill


def read_skill_name(skill: Path) -> str:
    text = (skill / "SKILL.md").read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        raise ValueError(f"{skill} 的 SKILL.md 缺少 frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{skill} 的 SKILL.md frontmatter 不完整")
    metadata = yaml.safe_load(parts[1]) or {}
    name = str(metadata.get("name", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise ValueError(f"{skill} 的 Skill name 无效")
    return name


def register_project_skills() -> dict[str, Path]:
    PROJECT_SKILLS_ROOT.mkdir(parents=True, exist_ok=True)
    desired: dict[str, Path] = {}
    for folder in SKILL_FOLDERS:
        base = ROOT / folder
        for skill_md in sorted(base.glob("*/SKILL.md")):
            skill = skill_md.parent.resolve()
            name = read_skill_name(skill)
            if name in desired and desired[name] != skill:
                raise RuntimeError(f"Skill name 重复：{name}")
            desired[name] = skill

    for name, skill in desired.items():
        link = PROJECT_SKILLS_ROOT / name
        if link.is_symlink():
            if link.resolve() == skill:
                continue
            link.unlink()
        elif link.exists():
            raise RuntimeError(f"项目 Skill 注册位置被普通文件占用：{link}")
        link.symlink_to(skill, target_is_directory=True)

    for existing in PROJECT_SKILLS_ROOT.iterdir():
        if existing.name not in desired and existing.is_symlink():
            existing.unlink()
    return desired


def public_models() -> list[dict[str, str]]:
    return [
        {"id": item["id"], "label": item["label"], "api_model": item["api_model"]}
        for item in CONFIG["models"]
    ]


def model_config(model_id: str) -> dict[str, str]:
    for item in CONFIG["models"]:
        if item["id"] == model_id:
            return item
    raise ValueError("不支持的模型")


def set_run(run_id: str, **changes: Any) -> None:
    with RUN_LOCK:
        RUNS[run_id].update(changes)


def add_log(run_id: str, message: str) -> None:
    with RUN_LOCK:
        RUNS[run_id]["logs"].append(redact(message))


def artifact_list(run_id: str, run_dir: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = str(path.relative_to(run_dir)).replace("\\", "/")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        encoded = urllib.parse.quote(relative, safe="/")
        items.append({"name": relative, "mime": mime, "url": f"/api/runs/{run_id}/files/{encoded}"})
    return items


def run_agent(
    run_id: str,
    skill_relative: str,
    prompt: str,
    model_id: str,
    session_id: str,
) -> None:
    try:
        if CODEX_CLI is None:
            raise RuntimeError("未找到可执行的本机 Codex CLI")
        skill = resolve_skill(skill_relative)
        model = model_config(model_id)
        run_dir = safe_relative(RUNS_ROOT, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        add_log(run_id, f"通过本机 Codex CLI 执行 {skill_relative}")
        add_log(run_id, f"使用模型 {model['label']}")

        selected_skill_name = read_skill_name(skill)
        cli_prompt = f"${selected_skill_name}\n\n{prompt}"

        cli_config = CONFIG.get("codex_cli", {})
        command = [
            str(CODEX_CLI),
            "-a", str(cli_config.get("approval_policy", "never")),
            "-s", str(cli_config.get("sandbox", "danger-full-access")),
            "-m", model["api_model"],
        ]
        if not session_id:
            command.extend(["-C", str(ROOT)])
        command.append("exec")
        if session_id:
            command.extend(["resume", "--json", session_id, "-"])
        else:
            command.extend(["--json", "--color", "never", "-"])

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=build_process_env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            creationflags=creation_flags,
        )
        stderr_lines: list[str] = []

        def read_stderr() -> None:
            assert process.stderr is not None
            for line in process.stderr:
                cleaned = redact(line.strip())
                if cleaned:
                    stderr_lines.append(cleaned)

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()
        assert process.stdin is not None
        process.stdin.write(cli_prompt)
        process.stdin.close()

        final_text = ""
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                add_log(run_id, f"CLI: {line}")
                continue
            event_type = str(event.get("type", ""))
            if event_type == "thread.started":
                new_session_id = str(event.get("thread_id", ""))
                if new_session_id:
                    session_id = new_session_id
                    set_run(run_id, session_id=session_id)
                add_log(run_id, "Codex 会话已建立")
            elif event_type == "turn.started":
                add_log(run_id, "Codex 开始处理")
            elif event_type in {"item.started", "item.completed"}:
                item = event.get("item") or {}
                item_type = str(item.get("type", ""))
                if item_type == "agent_message" and event_type == "item.completed":
                    text = str(item.get("text", ""))
                    if text:
                        final_text = text
                    add_log(run_id, "Codex 已生成答复")
                elif item_type == "command_execution":
                    if event_type == "item.started":
                        add_log(run_id, "执行本机命令（参数已隐藏）")
                    else:
                        add_log(run_id, f"命令完成：{item.get('status', 'unknown')}")
                elif item_type:
                    label = str(item.get("name") or item.get("server") or item_type)
                    action = "开始" if event_type == "item.started" else "完成"
                    add_log(run_id, f"{action}工具：{label}")
            elif event_type == "turn.completed":
                usage = event.get("usage") or {}
                add_log(run_id, f"Codex 执行完成，输出 tokens：{usage.get('output_tokens', 0)}")
            elif event_type in {"turn.failed", "error"}:
                detail = event.get("error") or event.get("message") or line
                add_log(run_id, f"Codex 错误：{detail}")

        return_code = process.wait()
        stderr_thread.join(timeout=2)
        if return_code != 0:
            for line in stderr_lines[-20:]:
                add_log(run_id, f"CLI: {line}")
            detail = stderr_lines[-1] if stderr_lines else f"退出码 {return_code}"
            raise RuntimeError(f"Codex CLI 执行失败：{detail}")
        if stderr_lines:
            add_log(run_id, f"Codex CLI 有 {len(stderr_lines)} 条非致命诊断，已折叠")
        if not final_text:
            final_text = "Codex CLI 已完成执行，但没有返回文字答复。"
        set_run(
            run_id,
            status="completed",
            result=redact(final_text),
            artifacts=artifact_list(run_id, run_dir),
            session_id=session_id,
            finished_at=time.time(),
        )
        add_log(run_id, "本机 Codex CLI 执行完成")
    except Exception as error:
        add_log(run_id, traceback.format_exc())
        set_run(run_id, status="failed", error=redact(str(error)), finished_at=time.time())


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin in self.allowed_origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    @staticmethod
    def allowed_origins() -> set[str]:
        port = int(CONFIG["server"]["port"])
        return {"null", f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        if origin not in self.allowed_origins():
            self.send_error(403)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def json_response(self, status: int, payload: Any) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            raise ValueError("请求内容为空或过大")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("请求内容必须是 JSON 对象")
        return payload

    def do_POST(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin not in self.allowed_origins():
            self.json_response(403, {"error": "不允许的请求来源"})
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self.json_response(415, {"error": "仅接受 application/json"})
            return
        try:
            path = urllib.parse.urlparse(self.path).path
            payload = self.read_json()
            if path == "/api/ratings/settings":
                self.json_response(200, RATINGS.update_levels(payload.get("rating_levels")))
                return
            if path == "/api/ratings/skill":
                self.json_response(200, RATINGS.update_skill(
                    str(payload.get("path", "")),
                    str(payload.get("rating", "")),
                    str(payload.get("note", "")),
                ))
                return
            if path == "/api/git/fetch":
                self.json_response(200, GIT.fetch())
                return
            if path == "/api/git/pull":
                self.json_response(200, GIT.pull())
                return
            if path == "/api/git/commit-push":
                self.json_response(200, GIT.commit_and_push(
                    str(payload.get("message", "")),
                    payload.get("files"),
                ))
                return
            if path == "/api/git/proxy":
                self.json_response(200, save_git_proxy_port(payload.get("port")))
                return
            if path != "/api/runs":
                self.json_response(404, {"error": "Not found"})
                return
            skill = str(payload.get("skill", ""))
            prompt = str(payload.get("prompt", ""))
            model = str(payload.get("model", CONFIG["agent"]["default_model"]))
            session_id = str(payload.get("session_id", "")).strip()
            resolve_skill(skill)
            model_config(model)
            if not prompt.strip():
                raise ValueError("请输入任务内容")
            if session_id and not re.fullmatch(r"[0-9a-fA-F-]{16,64}", session_id):
                raise ValueError("无效的 Codex 会话 ID")
            run_id = uuid.uuid4().hex[:12]
            with RUN_LOCK:
                RUNS[run_id] = {
                    "id": run_id,
                    "status": "running",
                    "skill": skill,
                    "model": model,
                    "logs": [],
                    "result": "",
                    "artifacts": [],
                    "error": "",
                    "session_id": session_id,
                    "created_at": time.time(),
                }
            threading.Thread(target=run_agent, args=(run_id, skill, prompt, model, session_id), daemon=True).start()
            self.json_response(202, {"id": run_id})
        except GitOperationError as error:
            self.json_response(409, {"error": str(error)})
        except Exception as error:
            self.json_response(400, {"error": str(error)})

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/config":
            self.json_response(200, {
                "models": public_models(),
                "default_model": CONFIG["agent"]["default_model"],
                "configured": CODEX_CLI is not None,
                "backend": "codex-cli",
            })
            return
        if path == "/api/ratings":
            self.json_response(200, RATINGS.load())
            return
        if path == "/api/git/status":
            try:
                self.json_response(200, GIT.status())
            except Exception as error:
                self.json_response(400, {"error": str(error)})
            return
        if path == "/api/git/diff":
            try:
                query = urllib.parse.parse_qs(parsed.query)
                self.json_response(200, GIT.diff(str((query.get("path") or [""])[0])))
            except Exception as error:
                self.json_response(400, {"error": str(error)})
            return
        if path.startswith("/api/runs/"):
            parts = path.split("/")
            run_id = parts[3] if len(parts) > 3 else ""
            with RUN_LOCK:
                run = dict(RUNS.get(run_id, {}))
            if not run:
                self.json_response(404, {"error": "运行记录不存在"})
                return
            if len(parts) >= 6 and parts[4] == "files":
                relative = urllib.parse.unquote("/".join(parts[5:]))
                try:
                    path = safe_relative(safe_relative(RUNS_ROOT, run_id, must_exist=True), relative, must_exist=True)
                except Exception:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(path.stat().st_size))
                self.end_headers()
                with path.open("rb") as stream:
                    self.wfile.write(stream.read())
                return
            self.json_response(200, run)
            return
        if path == "/":
            self.path = "/skills-showcase.html"
        super().do_GET()


def main() -> None:
    host = str(CONFIG["server"]["host"])
    port = int(CONFIG["server"]["port"])
    registered_skills = register_project_skills()
    status_changed = update_project_status(ROOT, CONFIG)
    print(f"Skill Playground: http://{host}:{port}")
    print(f"配置文件: {CONFIG_PATH}")
    print(f"项目状态文档: {'已更新' if status_changed else '无需更新'}")
    print(f"项目 Skills: 已向 Codex 注册 {len(registered_skills)} 个")
    print(f"执行后端: Codex CLI ({CODEX_CLI if CODEX_CLI else '未找到'})")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
