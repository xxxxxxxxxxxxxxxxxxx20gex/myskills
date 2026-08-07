from __future__ import annotations

import os
import re
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


RATING_KEYS = ("A", "B", "C")
DEFAULT_LEVELS = {
    "A": {"name": "推荐", "description": "效果稳定，可以直接使用", "color": "#15966f"},
    "B": {"name": "可用", "description": "基本可用，但仍有一些限制", "color": "#d98522"},
    "C": {"name": "待优化", "description": "效果不稳定，需要继续修改", "color": "#d34b4b"},
}


class RatingService:
    def __init__(self, root: Path, skill_folders: tuple[str, ...]) -> None:
        self.root = root
        self.path = root / "skill-metadata.yaml"
        self.skill_folders = skill_folders
        self.lock = threading.RLock()

    def valid_skill_paths(self) -> set[str]:
        return {
            str(skill_md.parent.relative_to(self.root)).replace("\\", "/")
            for folder in self.skill_folders
            for skill_md in (self.root / folder).glob("*/SKILL.md")
            if skill_md.is_file()
        }

    def load(self) -> dict[str, Any]:
        with self.lock:
            if not self.path.exists():
                return {"rating_levels": deepcopy(DEFAULT_LEVELS), "skills": {}}
            data = yaml.safe_load(self.path.read_text(encoding="utf-8-sig")) or {}
            levels = data.get("rating_levels") if isinstance(data.get("rating_levels"), dict) else {}
            skills = data.get("skills") if isinstance(data.get("skills"), dict) else {}
            normalized_levels = {
                key: self.validate_level(key, levels.get(key, DEFAULT_LEVELS[key]))
                for key in RATING_KEYS
            }
            valid_paths = self.valid_skill_paths()
            normalized_skills = {
                path: value
                for path, value in skills.items()
                if path in valid_paths and isinstance(value, dict) and value.get("rating") in RATING_KEYS
            }
            return {"rating_levels": normalized_levels, "skills": normalized_skills}

    @staticmethod
    def validate_level(key: str, value: Any) -> dict[str, str]:
        if key not in RATING_KEYS or not isinstance(value, dict):
            raise ValueError("评分等级必须是 A、B、C")
        name = str(value.get("name", "")).strip()
        description = str(value.get("description", "")).strip()
        color = str(value.get("color", "")).strip().lower()
        if not name or len(name) > 20:
            raise ValueError(f"{key} 等级名称长度应为 1–20 个字符")
        if len(description) > 120:
            raise ValueError(f"{key} 等级说明不能超过 120 个字符")
        if not re.fullmatch(r"#[0-9a-f]{6}", color):
            raise ValueError(f"{key} 等级颜色必须是六位十六进制颜色")
        return {"name": name, "description": description, "color": color}

    def save(self, data: dict[str, Any]) -> None:
        content = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        temporary = self.path.with_suffix(".yaml.tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, self.path)

    def update_levels(self, levels: Any) -> dict[str, Any]:
        if not isinstance(levels, dict):
            raise ValueError("评分等级配置无效")
        with self.lock:
            data = self.load()
            data["rating_levels"] = {
                key: self.validate_level(key, levels.get(key))
                for key in RATING_KEYS
            }
            self.save(data)
        return data

    def update_skill(self, path: str, rating: str, note: str) -> dict[str, Any]:
        normalized = path.replace("\\", "/").strip("/")
        if normalized not in self.valid_skill_paths():
            raise ValueError("Skill 路径无效或已不存在")
        rating = rating.strip().upper()
        note = note.strip()
        if rating and rating not in RATING_KEYS:
            raise ValueError("评分只能是 A、B、C 或未评分")
        if len(note) > 300:
            raise ValueError("评分备注不能超过 300 个字符")
        with self.lock:
            data = self.load()
            if rating:
                data["skills"][normalized] = {
                    "rating": rating,
                    "note": note,
                    "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                }
            else:
                data["skills"].pop(normalized, None)
            self.save(data)
        return data
