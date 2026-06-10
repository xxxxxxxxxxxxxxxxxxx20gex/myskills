#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


START = "<!-- local-operator-memory:start -->"
END = "<!-- local-operator-memory:end -->"


def memory_root() -> Path:
    return Path(os.environ.get("CODEX_LOCAL_MEMORY_DIR", Path.home() / ".codex-local-memory")).expanduser()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def run(project: Path, *args: str) -> str:
    try:
        out = subprocess.check_output(args, cwd=project, stderr=subprocess.DEVNULL, text=True)
        return out.strip()
    except Exception:
        return ""


def git_info(project: Path) -> dict:
    is_git = bool(run(project, "git", "rev-parse", "--is-inside-work-tree"))
    remote = ""
    branch = ""
    commit = ""
    status = ""
    if is_git:
        remote_lines = run(project, "git", "remote", "-v").splitlines()
        remote = remote_lines[0] if remote_lines else ""
        branch = run(project, "git", "branch", "--show-current")
        commit = run(project, "git", "rev-parse", "--short", "HEAD")
        status = "clean" if not run(project, "git", "status", "--short") else "dirty"
    return {
        "path": str(project),
        "name": project.name,
        "is_git": is_git,
        "remote": remote,
        "branch": branch,
        "commit": commit,
        "status": status,
        "last_seen": now_iso(),
        "summary": "",
    }


def managed_block(info: dict) -> str:
    return f"""{START}
## Local Operator Memory

- Path: {info['path']}
- Git repository: {info['is_git']}
- Remote: {info['remote']}
- Current branch: {info['branch']}
- Last observed commit: {info['commit']}
- Working tree: {info['status']}
- Last observed: {info['last_seen']}

### Operational Notes

- Keep durable project-specific instructions outside this managed block.
- This block may be refreshed by the local-operator-memory skill.
{END}"""


def update_agents(project: Path, info: dict) -> None:
    path = project / "AGENTS.md"
    block = managed_block(info)
    if not path.exists():
        path.write_text(f"# AGENTS.md\n\n{block}\n", encoding="utf-8")
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if START in text and END in text:
        before = text.split(START, 1)[0].rstrip()
        after = text.split(END, 1)[1].lstrip()
        path.write_text(f"{before}\n\n{block}\n\n{after}".rstrip() + "\n", encoding="utf-8")
    else:
        path.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")


def load_projects(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def update_index(info: dict) -> None:
    root = memory_root()
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "projects.json"
    projects = [p for p in load_projects(json_path) if p.get("path") != info["path"]]
    projects.append(info)
    projects.sort(key=lambda p: p.get("path", ""))
    json_path.write_text(json.dumps(projects, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = ["# Project Registry", ""]
    for p in projects:
        md.extend(
            [
                f"## {p.get('path', '')}",
                "",
                f"- Name: {p.get('name', '')}",
                f"- Git repository: {p.get('is_git', False)}",
                f"- Remote: {p.get('remote', '')}",
                f"- Branch: {p.get('branch', '')}",
                f"- Commit: {p.get('commit', '')}",
                f"- Status: {p.get('status', '')}",
                f"- Last seen: {p.get('last_seen', '')}",
                "",
            ]
        )
    (root / "projects.md").write_text("\n".join(md), encoding="utf-8")


def update(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        raise SystemExit(f"not a directory: {project}")
    info = git_info(project)
    update_agents(project, info)
    update_index(info)
    print(f"updated project context: {project}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Update AGENTS.md and project registry.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("update")
    p.add_argument("--project", required=True)
    p.set_defaults(func=update)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
