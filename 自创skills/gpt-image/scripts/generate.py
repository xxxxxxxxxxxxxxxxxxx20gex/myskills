#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "openai>=1.55",
#     "python-dotenv>=1.0",
# ]
# ///
"""Skill launcher for the local Right Code image relay."""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

_RIGHT_CODES_BASE_URL = "https://www.right.codes/draw"
_OPENAI_COMPAT_BASE_URL = f"{_RIGHT_CODES_BASE_URL}/v1"

SIZE_SHORTCUTS: dict[str, str] = {
    "1k": "1024x1024",
    "2k": "2048x2048",
    "4k": "3840x2160",
    "portrait": "1024x1536",
    "landscape": "1536x1024",
    "square": "1024x1024",
    "wide": "2048x1152",
    "tall": "2160x3840",
}


def _apply_right_codes_defaults() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))

    os.environ.setdefault("OPENAI_BASE_URL", _OPENAI_COMPAT_BASE_URL)
    os.environ.setdefault("RIGHT_CODES_BASE_URL", _RIGHT_CODES_BASE_URL)


def _parse_direct_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gpt-image",
        description="Call the local Right Code image relay.",
    )
    parser.add_argument("-p", "--prompt", required=True)
    parser.add_argument("-f", "--file")
    parser.add_argument("-i", "--image", action="append", default=[])
    parser.add_argument("-m", "--mask")
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", default=None)
    parser.add_argument("-n", "--n", type=int, default=1)
    parser.add_argument("--background", default=None)
    parser.add_argument("--moderation", default=None)
    parser.add_argument("--input-fidelity", dest="input_fidelity", default=None)
    parser.add_argument("--format", dest="output_format", default="png")
    parser.add_argument("--compression", dest="output_compression", default=None)
    parser.add_argument("--user", default=None)
    return parser.parse_args()


def _resolve_size(value: str) -> str:
    return SIZE_SHORTCUTS.get(value.lower(), value)


def _default_output_path(prompt: str, extension: str) -> Path:
    target_dir = Path(__file__).resolve().parents[1]
    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in prompt).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)[:30] or "image"
    return target_dir / f"{stamp}-{slug}.{extension}"


def _read_reference_images(paths_or_urls: list[str]) -> list[str]:
    images: list[str] = []
    for item in paths_or_urls:
        if item.startswith(("http://", "https://", "data:")):
            images.append(item)
            continue
        path = Path(item).expanduser()
        if not path.is_file():
            print(f"error: --image not found: {item}", file=sys.stderr)
            sys.exit(2)
        images.append(base64.b64encode(path.read_bytes()).decode("ascii"))
    return images


def _download_output(url: str, out_path: Path, index: int, count: int) -> Path:
    target = out_path
    if count > 1:
        target = out_path.with_name(f"{out_path.stem}_{index}{out_path.suffix}")
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 gpt-image-skill-right-codes/1.0",
            "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                target.write_bytes(response.read())
            return target
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(2 * attempt)
    raise RuntimeError(last_error)


def _run_right_codes_direct() -> int:
    """Direct Right Code generation call."""
    args = _parse_direct_args()
    if not os.environ.get("RIGHT_CODES_API_KEY"):
        print("error: RIGHT_CODES_API_KEY is not set.", file=sys.stderr)
        return 2

    if args.mask:
        print(
            "error: --mask is not supported by the baked-in Right Code fallback; "
            "install the upstream gpt-image CLI if you need inpainting.",
            file=sys.stderr,
        )
        return 2

    out_path = (
        Path(args.file).expanduser().resolve()
        if args.file
        else _default_output_path(args.prompt, args.output_format or "png")
    )

    headers = {
        "Authorization": f"Bearer {os.environ['RIGHT_CODES_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "image": _read_reference_images(args.image),
        "size": _resolve_size(args.size),
        "response_format": "url",
    }

    endpoint = f"{os.environ['RIGHT_CODES_BASE_URL'].rstrip('/')}/v1/images/generations"
    written: list[Path] = []
    for index in range(args.n):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            print(f"error: Right Code request failed: {exc}", file=sys.stderr)
            return 1

        items = result.get("data") or []
        if not items or not items[0].get("url"):
            print(f"error: no image URL in response: {result}", file=sys.stderr)
            return 1
        try:
            written.append(_download_output(items[0]["url"], out_path, index, args.n))
        except Exception as exc:
            print(f"error: failed to download generated image: {exc}", file=sys.stderr)
            return 1

    for path in written:
        print(path)
    return 0


def main() -> int:
    _apply_right_codes_defaults()
    return _run_right_codes_direct()


if __name__ == "__main__":
    sys.exit(main())
