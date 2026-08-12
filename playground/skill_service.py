from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from typing import Any

import yaml


SOURCE_FOLDERS = {
    "self": "自创skills",
    "tested": "已测skills",
    "pending": "待测skills",
}
FUNCTION_CATEGORIES = {"office", "visual", "academic", "media", "development", "system"}
TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".html", ".css",
    ".scss", ".ps1", ".sh", ".bat", ".cmd", ".sql", ".xml", ".csv",
}
IGNORED_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".agents"}
REFERENCE_ONLY_NAMES = {"license", "license.md", "license.txt", "copying", "copying.md", "copying.txt"}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".crt", ".cer"}
MAX_ANALYSIS_FILE_BYTES = 512 * 1024
MAX_ANALYSIS_CHARS = 120_000


def _is_sensitive(path: Path) -> bool:
    name = path.name.lower()
    if name in {".env", "credentials", "credentials.json", "auth.json", "secrets.json", "secrets.yaml", "secrets.yml"}:
        return True
    if name.startswith(".env.") and name != ".env.example":
        return True
    return name.startswith("secrets.") or path.suffix.lower() in SENSITIVE_SUFFIXES


def _atomic_yaml(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(temporary, path)


class SkillService:
    def __init__(self, root: Path, resolve_skill) -> None:
        self.root = root.resolve()
        self.resolve_skill = resolve_skill
        self.metadata_path = self.root / "skill-insights.yaml"
        self.lock = threading.RLock()

    def _load_metadata(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {"version": 1, "skills": {}}
        payload = yaml.safe_load(self.metadata_path.read_text(encoding="utf-8-sig")) or {}
        skills = payload.get("skills")
        return {"version": 1, "skills": skills if isinstance(skills, dict) else {}}

    def _save_metadata(self, payload: dict[str, Any]) -> None:
        _atomic_yaml(self.metadata_path, payload)

    @staticmethod
    def _parse_skill(skill: Path) -> tuple[dict[str, Any], list[str]]:
        text = (skill / "SKILL.md").read_text(encoding="utf-8-sig")
        metadata: dict[str, Any] = {}
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                metadata = yaml.safe_load(parts[1]) or {}
                body = parts[2]
        headings = [match.group(1).strip() for match in re.finditer(r"(?m)^#{1,4}\s+(.+?)\s*$", body)]
        return metadata, headings

    def list_skills(self) -> dict[str, Any]:
        with self.lock:
            saved = self._load_metadata().get("skills", {})
            items: list[dict[str, Any]] = []
            for status, folder in SOURCE_FOLDERS.items():
                base = self.root / folder
                if not base.exists():
                    continue
                for skill_md in sorted(base.glob("*/SKILL.md"), key=lambda path: path.parent.name.lower()):
                    skill = skill_md.parent
                    relative = skill.relative_to(self.root).as_posix()
                    metadata, headings = self._parse_skill(skill)
                    name = str(metadata.get("name") or skill.name).strip()
                    description = str(metadata.get("description") or "").strip()
                    entry = saved.get(relative) if isinstance(saved.get(relative), dict) else {}
                    items.append({
                        "path": relative,
                        "folder": skill.name,
                        "name": name,
                        "title": name.replace("-", " ").replace("_", " ").title(),
                        "summary": description or "尚未提供 Skill 简介。",
                        "source": "self" if status == "self" else "collected",
                        "status": "unclassified" if status == "self" else status,
                        "headings": headings,
                        "category": entry.get("category", ""),
                        "analysis": entry.get("analysis"),
                    })
            return {"skills": items, "sources": SOURCE_FOLDERS, "categories": sorted(FUNCTION_CATEGORIES)}

    def analysis_source(self, skill_relative: str) -> str:
        skill = self.resolve_skill(skill_relative)
        chunks: list[str] = []
        used = 0
        candidates = []
        for path in skill.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(skill)
            if path.is_symlink() or any(part in IGNORED_PARTS for part in relative.parts) or _is_sensitive(relative):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS or path.stat().st_size > MAX_ANALYSIS_FILE_BYTES:
                continue
            # Licenses and bundled font notices describe third-party assets, not what the Skill does.
            # Excluding them prevents large reference folders from overpowering SKILL.md and scripts.
            if path.name.lower() in REFERENCE_ONLY_NAMES or path.name.lower().endswith("-ofl.txt"):
                continue
            priority = 0 if relative.as_posix().lower() == "skill.md" else (1 if path.suffix.lower() in {".py", ".js", ".mjs", ".ts", ".ps1", ".sh"} else 2)
            candidates.append((priority, relative.as_posix().lower(), path, relative))
        for _, _, path, relative in sorted(candidates):
            content = path.read_text(encoding="utf-8-sig", errors="replace")
            chunk = f"\n--- FILE: {relative.as_posix()} ---\n{content}"
            if used + len(chunk) > MAX_ANALYSIS_CHARS:
                break
            chunks.append(chunk)
            used += len(chunk)
        return "".join(chunks)

    def save_analysis(self, skill_relative: str, analysis: dict[str, Any], model: str) -> dict[str, Any]:
        self.resolve_skill(skill_relative)
        with self.lock:
            metadata = self._load_metadata()
            entry = metadata["skills"].setdefault(skill_relative, {})
            entry["analysis"] = {
                **analysis,
                "model": model,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }
            self._save_metadata(metadata)
            return entry["analysis"]
