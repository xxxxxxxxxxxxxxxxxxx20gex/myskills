#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def format_dotenv_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def set_s2_api_key(env_path: Path, api_key: str) -> None:
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("S2_API_KEY cannot be empty")

    if env_path.is_file():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated_lines = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        key_expr = stripped[7:].strip() if stripped.startswith("export ") else stripped
        if key_expr.startswith("S2_API_KEY="):
            updated_lines.append(f"S2_API_KEY={format_dotenv_value(api_key)}")
            replaced = True
        else:
            updated_lines.append(line)

    if not replaced:
        updated_lines.append(f"S2_API_KEY={format_dotenv_value(api_key)}")

    env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def main() -> int:
    api_key = sys.stdin.read().strip()
    if not api_key:
        print("Error: provide the Semantic Scholar API key through stdin", file=sys.stderr)
        return 2

    env_path = Path(__file__).resolve().parent / ".env"
    set_s2_api_key(env_path, api_key)
    print(f"S2_API_KEY written to {env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
