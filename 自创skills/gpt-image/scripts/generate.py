#!/usr/bin/env python3
"""Generate, edit, or inpaint images with the OpenAI Images API."""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


OFFICIAL_BASE_URL = "https://api.openai.com/v1"
SIZE_SHORTCUTS = {
    "1k": "1024x1024",
    "2k": "2048x2048",
    "4k": "3840x2160",
    "portrait": "1024x1536",
    "landscape": "1536x1024",
    "square": "1024x1024",
    "wide": "2048x1152",
    "tall": "2160x3840",
}
OUTPUT_FORMATS = {"png", "jpeg", "webp"}


def load_skill_env() -> None:
    """Load only this skill's optional .env file without replacing shell variables."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gpt-image",
        description="Call the OpenAI-compatible Images API.",
    )
    parser.add_argument("-p", "--prompt", required=True)
    parser.add_argument("-f", "--file")
    parser.add_argument("-i", "--image", action="append", default=[])
    parser.add_argument("-m", "--mask")
    parser.add_argument("--model", default="gpt-image-2")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--quality", choices=("low", "medium", "high", "auto"))
    parser.add_argument("-n", "--n", type=int, default=1)
    parser.add_argument("--background", choices=("auto", "opaque", "transparent"))
    parser.add_argument("--moderation", choices=("auto", "low"))
    parser.add_argument("--input-fidelity", dest="input_fidelity", choices=("low", "high"))
    parser.add_argument("--format", dest="output_format", default="png", choices=OUTPUT_FORMATS)
    parser.add_argument("--compression", dest="output_compression", type=int)
    parser.add_argument("--user")
    args = parser.parse_args()
    if args.n < 1:
        parser.error("--n must be at least 1")
    if args.output_compression is not None and not 0 <= args.output_compression <= 100:
        parser.error("--compression must be between 0 and 100")
    if args.mask and not args.image:
        parser.error("--mask requires at least one --image")
    if args.mask and Path(args.mask).suffix.lower() != ".png":
        parser.error("--mask must be a PNG file")
    return args


def resolve_size(value: str) -> str:
    return SIZE_SHORTCUTS.get(value.lower(), value)


def default_output_path(prompt: str, extension: str) -> Path:
    target_dir = Path(__file__).resolve().parents[1] / "workspace"
    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in prompt).strip("-")
    slug = "-".join(part for part in slug.split("-") if part)[:30] or "image"
    return target_dir / f"{stamp}-{slug}.{extension}"


def api_base_url() -> str:
    base_url = os.environ.get("OPENAI_BASE_URL", OFFICIAL_BASE_URL).rstrip("/")
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


def api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY is not set. Add it to the skill root .env file.")
    return key


def request_json(url: str, payload: dict[str, Any], key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    return send_request(request)


def multipart_body(fields: dict[str, Any], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = f"----gpt-image-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        if value is None:
            continue
        chunks.extend((
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).encode("utf-8"),
            b"\r\n",
        ))
    for name, path in files:
        if not path.is_file():
            raise ValueError(f"{name} file not found: {path}")
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend((
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            path.read_bytes(),
            b"\r\n",
        ))
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def request_multipart(url: str, fields: dict[str, Any], files: list[tuple[str, Path]], key: str) -> dict[str, Any]:
    body, boundary = multipart_body(fields, files)
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    return send_request(request)


def send_request(request: urllib.request.Request) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"API request failed: {exc.reason}") from exc


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gpt-image-skill/2.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to download generated image: {last_error}")


def write_results(result: dict[str, Any], out_path: Path, count: int) -> list[Path]:
    items = result.get("data") or []
    if not items:
        raise RuntimeError(f"API response has no image data: {result}")
    written: list[Path] = []
    for index, item in enumerate(items):
        target = out_path if count == 1 else out_path.with_name(f"{out_path.stem}_{index + 1}{out_path.suffix}")
        if item.get("b64_json"):
            image_bytes = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            image_bytes = download(item["url"])
        else:
            raise RuntimeError(f"image item has neither b64_json nor url: {item}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image_bytes)
        written.append(target)
    return written


def optional_fields(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "model": args.model,
        "prompt": args.prompt,
        "n": args.n,
        "size": resolve_size(args.size),
        "quality": args.quality,
        "background": args.background,
        "output_format": args.output_format,
        "output_compression": args.output_compression,
        "moderation": args.moderation,
        "user": args.user,
    }


def main() -> int:
    load_skill_env()
    args = parse_args()
    try:
        key = api_key()
        out_path = Path(args.file).expanduser().resolve() if args.file else default_output_path(args.prompt, args.output_format)
        if args.image:
            fields = optional_fields(args)
            fields["input_fidelity"] = args.input_fidelity
            files = [("image[]", Path(value).expanduser()) for value in args.image]
            if args.mask:
                files.append(("mask", Path(args.mask).expanduser()))
            result = request_multipart(f"{api_base_url()}/images/edits", fields, files, key)
        else:
            result = request_json(f"{api_base_url()}/images/generations", optional_fields(args), key)
        for path in write_results(result, out_path, args.n):
            print(path)
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
