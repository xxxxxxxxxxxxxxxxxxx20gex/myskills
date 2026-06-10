#!/usr/bin/env python3
import argparse
import json
import os
import re
import shlex
import stat
from datetime import datetime
from pathlib import Path


CATEGORIES = {
    "machine",
    "users",
    "network",
    "multica-codex",
    "projects",
    "troubleshooting",
    "preferences",
}


def memory_root() -> Path:
    return Path(os.environ.get("CODEX_LOCAL_MEMORY_DIR", Path.home() / ".codex-local-memory")).expanduser()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def today() -> str:
    return datetime.now().astimezone().date().isoformat()


def ensure_root() -> Path:
    root = memory_root()
    root.mkdir(parents=True, exist_ok=True)
    for name in [
        "INDEX.md",
        "machine.md",
        "users.md",
        "network.md",
        "multica-codex.md",
        "projects.md",
        "troubleshooting.md",
        "preferences.md",
    ]:
        path = root / name
        if not path.exists():
            title = name.removesuffix(".md").replace("-", " ").title()
            path.write_text(f"# {title}\n\n", encoding="utf-8")
    lessons = root / "lessons.jsonl"
    lessons.touch(exist_ok=True)
    env = root / ".env"
    if not env.exists():
        env.write_text("# Local Operator Memory secrets. Do not print values.\n", encoding="utf-8")
    env.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return root


def append_markdown(root: Path, category: str, entry: dict) -> None:
    path = root / f"{category}.md"
    text = (
        f"\n## {entry['title']}\n\n"
        f"- Created: {entry['created_at']}\n"
        f"- Last confirmed: {entry['last_confirmed']}\n"
        f"- Scope: {entry['scope']}\n"
        f"- Confidence: {entry['confidence']}\n"
        f"- Evidence: {entry['evidence']}\n"
        f"- Tags: {', '.join(entry['tags']) if entry['tags'] else ''}\n\n"
        f"{entry['content'].rstrip()}\n"
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def add(args: argparse.Namespace) -> None:
    root = ensure_root()
    if args.category not in CATEGORIES:
        raise SystemExit(f"invalid category: {args.category}")
    entry = {
        "created_at": now_iso(),
        "last_confirmed": args.last_confirmed,
        "category": args.category,
        "title": args.title,
        "scope": args.scope,
        "content": args.content,
        "evidence": args.evidence,
        "confidence": args.confidence,
        "tags": args.tag or [],
    }
    with (root / "lessons.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    append_markdown(root, args.category, entry)
    print(f"recorded: {root / (args.category + '.md')}")


def iter_text_files(root: Path):
    for path in sorted(root.glob("*.md")):
        yield path
    lessons = root / "lessons.jsonl"
    if lessons.exists():
        yield lessons


def search(args: argparse.Namespace) -> None:
    root = ensure_root()
    terms = [t.lower() for t in re.findall(r"[\w./:-]+", args.query)]
    if not terms:
        raise SystemExit("empty query")
    matches = []
    for path in iter_text_files(root):
        text = redact_text(path.read_text(encoding="utf-8", errors="replace"))
        low = text.lower()
        score = sum(low.count(term) for term in terms)
        if score:
            matches.append((score, path, text))
    for score, path, text in sorted(matches, reverse=True)[: args.limit]:
        print(f"\n--- {path} (score {score}) ---")
        lines = text.splitlines()
        shown = 0
        last_end = -1
        for i, line in enumerate(lines, 1):
            low = line.lower()
            if any(term in low for term in terms):
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                if start <= last_end:
                    continue
                for j in range(start, end):
                    print(f"{j + 1}: {lines[j]}")
                last_end = end
                shown += 1
                if shown >= 3:
                    break


def parse_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        try:
            parts = shlex.split(value)
            value = parts[0] if parts else ""
        except ValueError:
            pass
        values[key] = value
    return values


def write_env(path: Path, values: dict) -> None:
    lines = ["# Local Operator Memory secrets. Do not print values."]
    for key in sorted(values):
        lines.append(f"{key}={shlex.quote(values[key])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def valid_key(key: str) -> bool:
    return bool(re.fullmatch(r"[A-Z_][A-Z0-9_]*", key))


def redact_text(text: str) -> str:
    patterns = [
        (r"(?i)(token|password|passwd|secret|api[_-]?key|authorization)([\"'\s:=]+)([^\"'\s,;]+)", r"\1\2<redacted>"),
        (r"(?i)(https?://)([^:@/\s]+):([^@/\s]+)@", r"\1<redacted>:<redacted>@"),
    ]
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text)
    return text


def secret(args: argparse.Namespace) -> None:
    root = ensure_root()
    env_path = root / ".env"
    values = parse_env(env_path)
    if args.secret_cmd == "set":
        if not valid_key(args.name):
            raise SystemExit("secret name must match [A-Z_][A-Z0-9_]*")
        values[args.name] = args.value
        write_env(env_path, values)
        print(f"stored secret key: {args.name}")
    elif args.secret_cmd == "get":
        if args.name not in values:
            raise SystemExit(f"missing secret key: {args.name}")
        print(values[args.name])
    elif args.secret_cmd == "list":
        for key in sorted(values):
            print(key)
    elif args.secret_cmd == "unset":
        values.pop(args.name, None)
        write_env(env_path, values)
        print(f"removed secret key: {args.name}")


def init(args: argparse.Namespace) -> None:
    root = ensure_root()
    print(root)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage local operator memory.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.set_defaults(func=init)

    p = sub.add_parser("add")
    p.add_argument("--category", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--scope", default="machine")
    p.add_argument("--content", required=True)
    p.add_argument("--evidence", default="")
    p.add_argument("--confidence", choices=["verified", "user-confirmed", "inferred"], default="verified")
    p.add_argument("--last-confirmed", default=today())
    p.add_argument("--tag", action="append")
    p.set_defaults(func=add)

    p = sub.add_parser("search")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=search)

    p = sub.add_parser("secret")
    secret_sub = p.add_subparsers(dest="secret_cmd", required=True)
    s = secret_sub.add_parser("set")
    s.add_argument("name")
    s.add_argument("value")
    s.set_defaults(func=secret)
    s = secret_sub.add_parser("get")
    s.add_argument("name")
    s.set_defaults(func=secret)
    s = secret_sub.add_parser("list")
    s.set_defaults(func=secret)
    s = secret_sub.add_parser("unset")
    s.add_argument("name")
    s.set_defaults(func=secret)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
