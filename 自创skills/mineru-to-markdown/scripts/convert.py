#!/usr/bin/env python3
import argparse
import http.client
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

AGENT_BASE = "https://mineru.net/api/v1/agent"
PRECISION_BASE = "https://mineru.net/api/v4"
SKILL_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = SKILL_DIR / "workspace"


def load_env_file(path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def request_json(method, url, body=None, headers=None, timeout=60):
    data = None
    final_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        final_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=final_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


def download_bytes(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read()


def upload_file(url, path):
    parsed = urllib.parse.urlparse(url)
    connection_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    target = urllib.parse.urlunparse(("", "", parsed.path, parsed.params, parsed.query, parsed.fragment))
    with open(path, "rb") as handle:
        body = handle.read()
    connection = connection_cls(parsed.netloc, timeout=300)
    try:
        connection.request("PUT", target, body=body, headers={"Content-Length": str(len(body))})
        response = connection.getresponse()
        detail = response.read().decode("utf-8", errors="replace")
        if response.status not in (200, 201):
            raise RuntimeError(f"Upload failed with HTTP {response.status}: {detail}")
    finally:
        connection.close()


def check_api_result(result, action):
    if result.get("code") != 0:
        raise RuntimeError(f"{action} failed: {result.get('msg', result)}")
    return result["data"]


def agent_payload(args):
    payload = {
        "language": args.language,
        "enable_table": not args.no_table,
        "is_ocr": args.ocr,
        "enable_formula": not args.no_formula,
    }
    if args.pages:
        payload["page_range"] = args.pages
    return payload


def poll_agent(task_id, timeout, interval):
    start = time.time()
    while time.time() - start < timeout:
        data = check_api_result(request_json("GET", f"{AGENT_BASE}/parse/{task_id}"), "Query")
        state = data["state"]
        if state == "done":
            return data["markdown_url"]
        if state == "failed":
            raise RuntimeError(f"MinerU task failed: {data.get('err_msg', 'unknown error')}")
        print(f"[{int(time.time() - start)}s] {state}", file=sys.stderr)
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for task_id={task_id}")


def parse_agent(source, args):
    payload = agent_payload(args)
    if is_url(source):
        payload["url"] = source
        data = check_api_result(request_json("POST", f"{AGENT_BASE}/parse/url", payload), "Submit URL")
    else:
        path = Path(source)
        payload["file_name"] = path.name
        data = check_api_result(request_json("POST", f"{AGENT_BASE}/parse/file", payload), "Create upload URL")
        upload_file(data["file_url"], path)
    task_id = data["task_id"]
    print(f"task_id={task_id}", file=sys.stderr)
    markdown_url = poll_agent(task_id, args.timeout, args.interval)
    print(f"markdown_url={markdown_url}", file=sys.stderr)
    return download_bytes(markdown_url).decode("utf-8"), markdown_url, None


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Accept": "*/*"}


def precision_payload(args):
    payload = {
        "model_version": args.model,
        "language": args.language,
        "enable_table": not args.no_table,
        "is_ocr": args.ocr,
        "enable_formula": not args.no_formula,
    }
    if args.pages:
        payload["page_ranges"] = args.pages
    return payload


def poll_precision_task(task_id, token, timeout, interval):
    start = time.time()
    while time.time() - start < timeout:
        data = check_api_result(
            request_json("GET", f"{PRECISION_BASE}/extract/task/{task_id}", headers=auth_headers(token)),
            "Query",
        )
        state = data["state"]
        if state == "done":
            return data["full_zip_url"]
        if state == "failed":
            raise RuntimeError(f"MinerU task failed: {data.get('err_msg', 'unknown error')}")
        print(f"[{int(time.time() - start)}s] {state}", file=sys.stderr)
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for task_id={task_id}")


def poll_precision_batch(batch_id, token, timeout, interval):
    start = time.time()
    while time.time() - start < timeout:
        data = check_api_result(
            request_json("GET", f"{PRECISION_BASE}/extract-results/batch/{batch_id}", headers=auth_headers(token)),
            "Query batch",
        )
        result = data["extract_result"][0]
        state = result["state"]
        if state == "done":
            return result["full_zip_url"]
        if state == "failed":
            raise RuntimeError(f"MinerU task failed: {result.get('err_msg', 'unknown error')}")
        print(f"[{int(time.time() - start)}s] {state}", file=sys.stderr)
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for batch_id={batch_id}")


def extract_zip_result(zip_bytes):
    assets = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        markdown = None
        for name in archive.namelist():
            if name.endswith("/full.md") or name == "full.md":
                markdown = archive.read(name).decode("utf-8")
            elif name.startswith("images/") or "/images/" in name:
                assets.append((Path(name).name if "/images/" in name else name, archive.read(name)))
    if markdown is None:
        raise RuntimeError("MinerU ZIP did not contain full.md")
    return markdown, assets


def parse_precision(source, args):
    token = args.token or os.environ.get("MINERU_API_TOKEN")
    if not token:
        raise RuntimeError("Precision mode requires --token or MINERU_API_TOKEN")
    payload = precision_payload(args)
    if is_url(source):
        payload["url"] = source
        data = check_api_result(
            request_json("POST", f"{PRECISION_BASE}/extract/task", payload, headers=auth_headers(token)),
            "Submit URL",
        )
        task_id = data["task_id"]
        print(f"task_id={task_id}", file=sys.stderr)
        zip_url = poll_precision_task(task_id, token, args.timeout, args.interval)
    else:
        path = Path(source)
        payload["files"] = [{"name": path.name}]
        data = check_api_result(
            request_json("POST", f"{PRECISION_BASE}/file-urls/batch", payload, headers=auth_headers(token)),
            "Create upload URL",
        )
        batch_id = data["batch_id"]
        print(f"batch_id={batch_id}", file=sys.stderr)
        upload_file(data["file_urls"][0], path)
        zip_url = poll_precision_batch(batch_id, token, args.timeout, args.interval)
    print(f"full_zip_url={zip_url}", file=sys.stderr)
    markdown, assets = extract_zip_result(download_bytes(zip_url))
    return markdown, None, assets


def write_assets(markdown, out_dir, base_url=None, assets=None):
    written = 0
    failed = 0
    if assets:
        images_dir = out_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        for name, content in assets:
            (images_dir / Path(name).name).write_bytes(content)
            written += 1
        print(f"assets_written={written}", file=sys.stderr)
        return
    if not base_url:
        return
    refs = set(re.findall(r"!\[[^\]]*\]\((images/[^)]+)\)", markdown))
    refs.update(re.findall(r"<img[^>]+src=[\"'](images/[^\"']+)[\"']", markdown, flags=re.I))
    for ref in refs:
        target = out_dir / urllib.parse.unquote(ref)
        target.parent.mkdir(parents=True, exist_ok=True)
        url = urllib.parse.urljoin(base_url, ref)
        try:
            target.write_bytes(download_bytes(url))
            written += 1
        except Exception as exc:
            failed += 1
            print(f"asset_failed={ref}: {exc}", file=sys.stderr)
    print(f"assets_written={written} assets_failed={failed}", file=sys.stderr)


def is_url(value):
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in ("http", "https")


def default_output_path(source):
    if is_url(source):
        parsed = urllib.parse.urlparse(source)
        name = Path(parsed.path).stem or "mineru-output"
    else:
        name = Path(source).stem
    return WORKSPACE_DIR / name / f"{name}.md"


def resolve_mode(args):
    if args.mode != "auto":
        return args.mode
    if args.token or os.environ.get("MINERU_API_TOKEN"):
        return "precision"
    return "agent"


def main():
    parser = argparse.ArgumentParser(description="Convert a document to Markdown with MinerU API.")
    parser.add_argument("source", help="Local file path or HTTP(S) URL")
    parser.add_argument("--out", help="Output Markdown path")
    parser.add_argument("--mode", choices=("auto", "agent", "precision"), default="auto")
    parser.add_argument("--token", help="MinerU API token for precision mode")
    parser.add_argument("--model", default="vlm", help="Precision model: vlm, pipeline, or MinerU-HTML")
    parser.add_argument("--language", default="ch")
    parser.add_argument("--pages", help="Page range, for example 1-10")
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--no-table", action="store_true")
    parser.add_argument("--no-formula", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--interval", type=int, default=3)
    args = parser.parse_args()
    load_env_file(SKILL_DIR / ".env")

    if not is_url(args.source) and not Path(args.source).is_file():
        raise FileNotFoundError(args.source)

    mode = resolve_mode(args)
    print(f"mode={mode}", file=sys.stderr)
    markdown, base_url, assets = parse_precision(args.source, args) if mode == "precision" else parse_agent(args.source, args)
    out_path = Path(args.out) if args.out else default_output_path(args.source)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    write_assets(markdown, out_path.parent, base_url, assets)
    print(out_path)


if __name__ == "__main__":
    main()
