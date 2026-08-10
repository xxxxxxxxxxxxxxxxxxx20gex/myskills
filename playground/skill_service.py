from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


SOURCE_FOLDERS = {
    "self": "自创skills",
    "tested": "已测skills",
    "pending": "待测skills",
}
FOLDER_SOURCES = {folder: source for source, folder in SOURCE_FOLDERS.items()}
FUNCTION_CATEGORIES = {"office", "visual", "academic", "media", "development", "system"}
TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".html", ".css",
    ".scss", ".ps1", ".sh", ".bat", ".cmd", ".sql", ".xml", ".csv",
}
IGNORED_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".agents"}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx", ".crt", ".cer"}
MAX_IMPORT_BYTES = 50 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 150 * 1024 * 1024
MAX_IMPORT_FILES = 2000
MAX_PREVIEW_BYTES = 512 * 1024


def _is_sensitive(path: PurePosixPath | Path) -> bool:
    name = path.name.lower()
    if name in {".env", "credentials", "credentials.json", "auth.json", "secrets.json", "secrets.yaml", "secrets.yml"}:
        return True
    if name.startswith(".env.") and name != ".env.example":
        return True
    if name.startswith("secrets.") or path.suffix.lower() in SENSITIVE_SUFFIXES:
        return True
    return False


def _atomic_yaml(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(temporary, path)


class SkillService:
    def __init__(self, root: Path, resolve_skill, read_skill_name) -> None:
        self.root = root.resolve()
        self.resolve_skill = resolve_skill
        self.read_skill_name = read_skill_name
        self.metadata_path = self.root / "skill-insights.yaml"
        self.trash_root = self.root / ".skill-trash"
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

    def _relative_file(self, skill_relative: str, file_relative: str) -> Path:
        skill = self.resolve_skill(skill_relative)
        normalized = PurePosixPath(file_relative.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError("文件路径无效")
        target = (skill / Path(*normalized.parts)).resolve()
        if target != skill and skill not in target.parents:
            raise ValueError("文件路径超出了 Skill 目录")
        if not target.is_file():
            raise FileNotFoundError(file_relative)
        return target

    def tree(self, skill_relative: str) -> dict[str, Any]:
        skill = self.resolve_skill(skill_relative)
        entries: list[dict[str, Any]] = []
        for path in sorted(skill.rglob("*"), key=lambda item: (not item.is_dir(), item.as_posix().lower())):
            relative = path.relative_to(skill)
            if any(part in IGNORED_PARTS for part in relative.parts):
                continue
            item = {"path": relative.as_posix(), "name": path.name, "type": "directory" if path.is_dir() else "file"}
            if path.is_file():
                item["size"] = path.stat().st_size
                item["readable"] = not path.is_symlink() and not _is_sensitive(relative) and path.suffix.lower() in TEXT_EXTENSIONS and path.stat().st_size <= MAX_PREVIEW_BYTES
            entries.append(item)
        return {"path": skill_relative, "entries": entries}

    def read_file(self, skill_relative: str, file_relative: str) -> dict[str, Any]:
        target = self._relative_file(skill_relative, file_relative)
        relative = target.relative_to(self.resolve_skill(skill_relative))
        if _is_sensitive(relative):
            raise ValueError("敏感凭据文件不允许在页面中读取")
        if target.suffix.lower() not in TEXT_EXTENSIONS:
            raise ValueError("该文件类型不支持文本预览")
        if target.stat().st_size > MAX_PREVIEW_BYTES:
            raise ValueError("文件超过 512 KB，不能在页面中预览")
        return {"path": relative.as_posix(), "content": target.read_text(encoding="utf-8-sig", errors="replace")}

    def export_zip(self, skill_relative: str) -> tuple[str, bytes, list[str]]:
        skill = self.resolve_skill(skill_relative)
        buffer = io.BytesIO()
        excluded: list[str] = []
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(skill.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(skill)
                if path.is_symlink() or any(part in IGNORED_PARTS for part in relative.parts) or _is_sensitive(relative):
                    excluded.append(relative.as_posix())
                    continue
                archive.write(path, f"{skill.name}/{relative.as_posix()}")
        return f"{skill.name}.zip", buffer.getvalue(), excluded

    @staticmethod
    def _safe_archive_entries(archive: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], str | None]:
        files = [item for item in archive.infolist() if not item.is_dir()]
        if not files or len(files) > MAX_IMPORT_FILES:
            raise ValueError("压缩包为空或文件数量超过限制")
        if sum(item.file_size for item in files) > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("压缩包解压后的总大小超过 150 MB")
        paths = [PurePosixPath(item.filename.replace("\\", "/")) for item in files]
        for path in paths:
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError("压缩包包含不安全路径")
            if any(part in IGNORED_PARTS for part in path.parts) or _is_sensitive(path):
                raise ValueError(f"压缩包包含不允许导入的文件：{path.as_posix()}")
        roots = {path.parts[0] for path in paths}
        prefix = next(iter(roots)) if len(roots) == 1 and all(len(path.parts) > 1 for path in paths) else None
        normalized = [PurePosixPath(*path.parts[1:]) if prefix else path for path in paths]
        if PurePosixPath("SKILL.md") not in normalized:
            raise ValueError("压缩包根目录缺少 SKILL.md")
        return files, prefix

    def import_zip(self, data: bytes, source: str, category: str) -> dict[str, Any]:
        if len(data) <= 0 or len(data) > MAX_IMPORT_BYTES:
            raise ValueError("ZIP 文件为空或超过 50 MB")
        if source not in SOURCE_FOLDERS:
            raise ValueError("导入分类无效")
        if category not in FUNCTION_CATEGORIES:
            raise ValueError("功能分类无效")
        with self.lock, zipfile.ZipFile(io.BytesIO(data)) as archive:
            files, prefix = self._safe_archive_entries(archive)
            with tempfile.TemporaryDirectory(prefix="skill-import-", dir=self.root) as temporary:
                temp_root = Path(temporary)
                for item in files:
                    original = PurePosixPath(item.filename.replace("\\", "/"))
                    relative = PurePosixPath(*original.parts[1:]) if prefix else original
                    target = temp_root / Path(*relative.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(item) as source_stream, target.open("wb") as target_stream:
                        shutil.copyfileobj(source_stream, target_stream)
                name = self.read_skill_name(temp_root)
                folder_name = prefix or name
                if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", folder_name):
                    folder_name = name
                destination = self.root / SOURCE_FOLDERS[source] / folder_name
                if destination.exists():
                    raise FileExistsError(f"Skill 已存在：{destination.relative_to(self.root).as_posix()}")
                shutil.move(str(temp_root), str(destination))
            relative = destination.relative_to(self.root).as_posix()
            metadata = self._load_metadata()
            metadata["skills"].setdefault(relative, {})["category"] = category
            self._save_metadata(metadata)
            return {"path": relative, "name": name}

    def delete(self, skill_relative: str, confirmation: str) -> dict[str, Any]:
        if confirmation != skill_relative:
            raise ValueError("删除确认内容不匹配")
        with self.lock:
            skill = self.resolve_skill(skill_relative)
            self.trash_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            destination = self.trash_root / f"{stamp}-{skill.parent.name}-{skill.name}"
            counter = 1
            while destination.exists():
                destination = self.trash_root / f"{stamp}-{skill.parent.name}-{skill.name}-{counter}"
                counter += 1
            shutil.move(str(skill), str(destination))
            metadata = self._load_metadata()
            metadata["skills"].pop(skill_relative, None)
            self._save_metadata(metadata)
            return {"deleted": skill_relative, "trash": destination.relative_to(self.root).as_posix()}

    def move(self, skill_relative: str, target_source: str) -> dict[str, Any]:
        if target_source not in SOURCE_FOLDERS:
            raise ValueError("维护标签无效")
        with self.lock:
            skill = self.resolve_skill(skill_relative)
            current_source = FOLDER_SOURCES.get(skill.parent.name)
            if current_source is None:
                raise ValueError("当前 Skill 不在可维护目录中")
            if current_source == target_source:
                return {"old_path": skill_relative, "new_path": skill_relative, "source": target_source, "changed": False}
            destination = self.root / SOURCE_FOLDERS[target_source] / skill.name
            if destination.exists():
                raise FileExistsError(f"目标标签下已存在同名 Skill：{destination.relative_to(self.root).as_posix()}")
            old_path = skill.relative_to(self.root).as_posix()
            new_path = destination.relative_to(self.root).as_posix()
            metadata = self._load_metadata()
            old_entry = metadata["skills"].pop(old_path, None)
            try:
                shutil.move(str(skill), str(destination))
                if old_entry is not None:
                    metadata["skills"][new_path] = old_entry
                self._save_metadata(metadata)
            except Exception:
                if destination.exists() and not skill.exists():
                    shutil.move(str(destination), str(skill))
                raise
            return {"old_path": old_path, "new_path": new_path, "source": target_source, "changed": True}

    def analysis_source(self, skill_relative: str) -> str:
        skill = self.resolve_skill(skill_relative)
        chunks: list[str] = []
        used = 0
        for path in sorted(skill.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(skill)
            if path.is_symlink() or any(part in IGNORED_PARTS for part in relative.parts) or _is_sensitive(relative):
                continue
            if path.suffix.lower() not in TEXT_EXTENSIONS or path.stat().st_size > MAX_PREVIEW_BYTES:
                continue
            content = path.read_text(encoding="utf-8-sig", errors="replace")
            chunk = f"\n--- FILE: {relative.as_posix()} ---\n{content}"
            if used + len(chunk) > 120_000:
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
