#!/usr/bin/env python3
import argparse
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


PROVIDERS = (
    "litterbox.catbox.moe",
    "temp.sh",
    "blob.zip",
    "cliupload.com",
    "file.io",
    "transfer.sh",
    "0x0.st",
)


def curl_available():
    return shutil.which("curl") is not None


def safe_name(path):
    name = Path(path).name.strip() or "upload"
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)


def zip_directory(directory, workdir):
    directory = Path(directory)
    archive = Path(workdir) / f"{safe_name(directory)}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(directory.rglob("*")):
            if item.is_file():
                zf.write(item, item.relative_to(directory.parent))
    return archive


def prepare_path(path, workdir):
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.is_dir():
        return p, zip_directory(p, workdir), True
    return p, p, False


def check_size(upload_path, max_mb):
    size = upload_path.stat().st_size
    limit = max_mb * 1024 * 1024
    if size > limit:
        raise ValueError(f"{upload_path} is {size} bytes, over --max-mb {max_mb}")
    return size


def request_put(url, upload_path, content_type=None):
    data = upload_path.read_bytes()
    headers = {"User-Agent": "codex-temp-file-uploader/1.0"}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method="PUT")
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8", errors="replace").strip()
        if resp.status >= 400:
            raise RuntimeError(f"HTTP {resp.status}: {body}")
        return body


def request_multipart_python(url, upload_path):
    boundary = "----codex-temp-upload-boundary"
    content_type = mimetypes.guess_type(upload_path.name)[0] or "application/octet-stream"
    file_data = upload_path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        (
            'Content-Disposition: form-data; name="file"; '
            f'filename="{upload_path.name}"\r\n'
        ).encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        file_data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    data = b"".join(parts)
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "codex-temp-file-uploader/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace").strip()


def request_fileio(upload_path):
    body = request_multipart_python("https://file.io/", upload_path)
    parsed = json.loads(body)
    if not parsed.get("success"):
        raise RuntimeError(parsed.get("message") or body)
    return parsed.get("link")


def request_litterbox_catbox(upload_path):
    if not curl_available():
        raise RuntimeError("curl is required for this provider")
    result = subprocess.run(
        [
            "curl",
            "-fsS",
            "-F",
            "reqtype=fileupload",
            "-F",
            "time=1h",
            "-F",
            f"fileToUpload=@{upload_path}",
            "https://litterbox.catbox.moe/resources/internals/api.php",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"curl exited {result.returncode}")
    return result.stdout.strip()


def request_temp_sh(upload_path):
    body = request_multipart_python("https://temp.sh/upload", upload_path)
    return body.splitlines()[-1].strip()


def request_blob_zip(upload_path):
    body = request_multipart_python("https://blob.zip", upload_path)
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body.splitlines()[-1].strip()
    return parsed.get("url") or parsed.get("link") or parsed.get("downloadUrl") or body


def request_form_curl(url, upload_path):
    if not curl_available():
        raise RuntimeError("curl is required for this provider")
    result = subprocess.run(
        ["curl", "-fsS", "-F", f"file=@{upload_path}", url],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"curl exited {result.returncode}")
    return result.stdout.strip()


def upload(provider, upload_path):
    name = urllib.parse.quote(upload_path.name)
    content_type = mimetypes.guess_type(upload_path.name)[0] or "application/octet-stream"
    if provider == "litterbox.catbox.moe":
        return request_litterbox_catbox(upload_path)
    if provider == "temp.sh":
        return request_temp_sh(upload_path)
    if provider == "blob.zip":
        return request_blob_zip(upload_path)
    if provider == "cliupload.com":
        return request_put(f"https://cliupload.com/{name}", upload_path, content_type)
    if provider == "transfer.sh":
        return request_put(f"https://transfer.sh/{name}", upload_path, content_type)
    if provider == "file.io":
        return request_fileio(upload_path)
    if provider == "0x0.st":
        return request_form_curl("https://0x0.st", upload_path)
    raise ValueError(f"Unknown provider: {provider}")


def ordered_providers(selected):
    if selected == "auto":
        return PROVIDERS
    if selected not in PROVIDERS:
        raise ValueError(f"Unknown provider: {selected}")
    return (selected,)


def main():
    parser = argparse.ArgumentParser(
        description="Upload files/directories to temporary public file links."
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to upload")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=("auto",) + PROVIDERS,
        help="Provider to use; default tries all supported providers",
    )
    parser.add_argument(
        "--max-mb",
        type=int,
        default=100,
        help="Refuse uploads larger than this size after zipping directories",
    )
    args = parser.parse_args()

    uploads = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="temp-public-upload-") as workdir:
        for original in args.paths:
            try:
                source_path, upload_path, zipped = prepare_path(original, workdir)
                size = check_size(upload_path, args.max_mb)
            except Exception as error:
                failures.append({"path": original, "error": str(error)})
                continue

            provider_errors = []
            for provider in ordered_providers(args.provider):
                try:
                    url = upload(provider, upload_path)
                    if not url:
                        raise RuntimeError("empty response")
                    uploads.append(
                        {
                            "path": str(source_path),
                            "uploaded_file": str(upload_path),
                            "zipped": zipped,
                            "size_bytes": size,
                            "provider": provider,
                            "url": url,
                        }
                    )
                    break
                except Exception as error:
                    provider_errors.append({"provider": provider, "error": str(error)})
            else:
                failures.append({"path": str(source_path), "errors": provider_errors})

    print(json.dumps({"uploads": uploads, "failures": failures}, ensure_ascii=False, indent=2))
    return 1 if failures and not uploads else 0


if __name__ == "__main__":
    sys.exit(main())
