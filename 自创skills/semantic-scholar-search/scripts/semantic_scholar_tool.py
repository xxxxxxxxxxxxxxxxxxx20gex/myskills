#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import requests

SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
RATE_LIMIT_SECONDS = 1.0
DEFAULT_TIMEOUT_SECONDS = 20
LOCK_WAIT_TIMEOUT_SECONDS = 120
STALE_LOCK_SECONDS = 160
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRY_BACKOFF_MAX_SECONDS = 8.0
RETRY_BACKOFF_JITTER_SECONDS = 0.25
STATIC_GET_ENDPOINTS = {
    "paper/search",
    "paper/search/bulk",
    "paper/search/match",
    "paper/autocomplete",
    "snippet/search",
    "author/search",
}
POST_ENDPOINTS = {
    "paper/batch",
    "author/batch",
}
PAPER_RELATION_ENDPOINTS = {"authors", "citations", "references"}


class ToolError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@contextmanager
def semantic_scholar_rate_limit_lock():
    state_dir = os.path.join(tempfile.gettempdir(), "semantic-scholar-search-skill")
    os.makedirs(state_dir, exist_ok=True)
    lock_path = os.path.join(state_dir, "rate-limit.lockdir")
    state_path = os.path.join(state_dir, "last-request.json")

    lock_wait_started = time.monotonic()
    while True:
        try:
            os.mkdir(lock_path)
            break
        except FileExistsError:
            if time.monotonic() - lock_wait_started > LOCK_WAIT_TIMEOUT_SECONDS:
                raise ToolError(
                    "RATE_LIMIT_LOCK_TIMEOUT",
                    "Timed out waiting for the local Semantic Scholar rate-limit lock",
                )
            try:
                lock_age_seconds = time.time() - os.path.getmtime(lock_path)
            except OSError:
                time.sleep(0.2)
                continue
            if lock_age_seconds > STALE_LOCK_SECONDS:
                try:
                    os.rmdir(lock_path)
                except OSError:
                    pass
            time.sleep(0.2)

    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as state_file:
                last_request_at = float(json.load(state_file).get("last_request_at", 0))
            wait_seconds = RATE_LIMIT_SECONDS - (time.monotonic() - last_request_at)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
        with open(state_path, "w", encoding="utf-8") as state_file:
            json.dump({"last_request_at": time.monotonic()}, state_file)
        yield
    finally:
        try:
            os.rmdir(lock_path)
        except FileNotFoundError:
            pass


def require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ToolError("INVALID_REQUEST", f"{path} must be a JSON object")
    return value


def optional_object(value: Any, path: str) -> dict[str, Any]:
    if value is None:
        return {}
    return require_object(value, path)


def optional_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ToolError("INVALID_REQUEST", f"{path} must be a non-empty string")
    return value.strip()


def optional_int(value: Any, path: str, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise ToolError("INVALID_REQUEST", f"{path} must be an integer")
    if value < minimum or value > maximum:
        raise ToolError("INVALID_REQUEST", f"{path} must be between {minimum} and {maximum}")
    return value


def read_request() -> dict[str, Any]:
    raw_request = sys.stdin.read()
    if not raw_request.strip():
        raise ToolError("INVALID_JSON", "Expected one JSON request object on stdin")
    try:
        request = json.loads(raw_request)
    except json.JSONDecodeError as exc:
        raise ToolError("INVALID_JSON", f"stdin is not valid JSON: {exc}") from exc
    return require_object(request, "request")


def normalize_endpoint(endpoint: str) -> str:
    return endpoint.strip().strip("/")


def split_id_endpoint(remainder: str) -> tuple[str, str | None]:
    for suffix in PAPER_RELATION_ENDPOINTS:
        marker = f"/{suffix}"
        if remainder.endswith(marker):
            return remainder[: -len(marker)], suffix
    return remainder, None


def is_valid_paper_id_path_segment(paper_id: str) -> bool:
    if not paper_id or paper_id in {"batch", "search", "autocomplete"}:
        return False
    if "/" not in paper_id:
        return True
    return paper_id.startswith(("DOI:", "URL:"))


def resolve_endpoint_method(endpoint: str) -> str | None:
    normalized = endpoint.strip().rstrip("/")
    if not normalized:
        return None
    if normalized in STATIC_GET_ENDPOINTS:
        return "GET"
    if normalized in POST_ENDPOINTS:
        return "POST"
    if normalized.startswith("paper/"):
        remainder = normalized[len("paper/") :]
        paper_id, _relation = split_id_endpoint(remainder)
        if not is_valid_paper_id_path_segment(paper_id):
            return None
        return "GET"
    if normalized.startswith("author/"):
        parts = normalized.split("/")
        if len(parts) not in {2, 3}:
            return None
        if len(parts) == 3 and parts[2] != "papers":
            return None
        if not parts[1] or parts[1] in {"batch", "search"}:
            return None
        return "GET"
    return None


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def validate_batch_payload(endpoint: str, payload: dict[str, Any]) -> None:
    if endpoint not in POST_ENDPOINTS:
        return
    ids = payload.get("ids")
    if not isinstance(ids, list) or not ids:
        raise ToolError("INVALID_REQUEST", f"{endpoint} payload requires a non-empty ids array")
    for index, item in enumerate(ids):
        if not isinstance(item, str) or not item.strip():
            raise ToolError("INVALID_REQUEST", f"payload.ids[{index}] must be a non-empty string")
    if endpoint == "paper/batch" and len(ids) > 500:
        raise ToolError("INVALID_REQUEST", "paper/batch accepts at most 500 paper IDs")
    if endpoint == "author/batch" and len(ids) > 1000:
        raise ToolError("INVALID_REQUEST", "author/batch accepts at most 1000 author IDs")


def validate_semantic_request(endpoint: str, params: dict[str, Any], payload: dict[str, Any]) -> None:
    if resolve_endpoint_method(endpoint) is None:
        raise ToolError("INVALID_REQUEST", f"Unsupported endpoint: {endpoint}")

    validate_batch_payload(endpoint, payload)

    if endpoint in {"paper/search", "paper/search/bulk", "paper/search/match", "paper/autocomplete", "snippet/search"}:
        query = params.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ToolError("INVALID_REQUEST", f"{endpoint} requires params.query")

    limit = params.get("limit")
    offset = params.get("offset", 0)
    if limit is None:
        return

    limit_i = safe_int(limit, -1)
    offset_i = safe_int(offset, 0)
    if limit_i < 0:
        raise ToolError("INVALID_REQUEST", "params.limit must be a non-negative integer")
    if offset_i < 0:
        raise ToolError("INVALID_REQUEST", "params.offset must be a non-negative integer")

    if endpoint == "paper/search":
        if limit_i > 100:
            raise ToolError("INVALID_REQUEST", "paper/search params.limit must be <= 100")
        if offset_i + limit_i >= 1000:
            raise ToolError("INVALID_REQUEST", "paper/search params.offset + params.limit must be < 1000")

    if endpoint == "author/search":
        if limit_i > 1000:
            raise ToolError("INVALID_REQUEST", "author/search params.limit must be <= 1000")
        if offset_i + limit_i >= 10000:
            raise ToolError("INVALID_REQUEST", "author/search params.offset + params.limit must be < 10000")

    if endpoint.endswith(("/authors", "/references", "/citations", "/papers")) and limit_i > 1000:
        raise ToolError("INVALID_REQUEST", "relation endpoints require params.limit <= 1000")


def is_name_resolution_error(exc: requests.exceptions.ConnectionError) -> bool:
    message = str(exc)
    dns_markers = (
        "NameResolutionError",
        "Failed to resolve",
        "Temporary failure in name resolution",
        "nodename nor servname provided",
        "getaddrinfo failed",
    )
    return any(marker in message for marker in dns_markers)


def retry_after_seconds(response: requests.Response) -> float | None:
    raw_value = response.headers.get("Retry-After")
    if not raw_value:
        return None
    try:
        return max(0.0, float(raw_value))
    except ValueError:
        return None


def retry_delay_seconds(attempt: int, response: requests.Response | None = None) -> float:
    delay = min(RETRY_BACKOFF_MAX_SECONDS, RETRY_BACKOFF_BASE_SECONDS * (2**attempt))
    if response is not None:
        retry_after = retry_after_seconds(response)
        if retry_after is not None:
            delay = max(delay, retry_after)
    return delay + random.uniform(0, RETRY_BACKOFF_JITTER_SECONDS)


def should_retry_exception(exc: requests.exceptions.RequestException) -> bool:
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if isinstance(exc, requests.exceptions.ConnectionError):
        return not is_name_resolution_error(exc)
    return False


def read_s2_api_key_from_dotenv(env_path: Path) -> str | None:
    if not env_path.is_file():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        if key.strip() != "S2_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            quote = value[0]
            value = value[1:-1]
            if quote == '"':
                unescaped = []
                escaping = False
                for char in value:
                    if escaping:
                        unescaped.append(char if char in {'"', "\\"} else f"\\{char}")
                        escaping = False
                    elif char == "\\":
                        escaping = True
                    else:
                        unescaped.append(char)
                if escaping:
                    unescaped.append("\\")
                value = "".join(unescaped)
        return value or None
    return None


def resolve_s2_api_key() -> str | None:
    env_value = (os.getenv("S2_API_KEY") or "").strip()
    if env_value:
        return env_value
    return read_s2_api_key_from_dotenv(Path(__file__).resolve().parent / ".env")


def execute_semantic_scholar_call(
    endpoint: str,
    params: dict[str, Any],
    payload: dict[str, Any],
    timeout_seconds: int,
    api_key: str | None,
) -> dict[str, Any]:
    method = resolve_endpoint_method(endpoint)
    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    url = f"{SEMANTIC_SCHOLAR_BASE_URL}/{endpoint}"
    errors = []
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            with semantic_scholar_rate_limit_lock():
                if method == "POST":
                    response = requests.post(url, params=params, json=payload, headers=headers, timeout=timeout_seconds)
                else:
                    response = requests.get(url, params=params, headers=headers, timeout=timeout_seconds)
            if response.status_code in RETRY_STATUS_CODES:
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    time.sleep(retry_delay_seconds(attempt, response))
                    continue
                if response.status_code == 429:
                    raise ToolError(
                        "SEMANTIC_SCHOLAR_RATE_LIMITED",
                        "Semantic Scholar returned 429 after retries",
                        {"status_code": response.status_code},
                    )
            response.raise_for_status()
            try:
                return response.json()
            except ValueError as exc:
                raise ToolError(
                    "SEMANTIC_SCHOLAR_RESPONSE_INVALID",
                    "Semantic Scholar returned non-JSON response",
                    {"raw_text": response.text[:500]},
                ) from exc
        except requests.exceptions.Timeout as exc:
            if attempt < MAX_RETRY_ATTEMPTS - 1 and should_retry_exception(exc):
                time.sleep(retry_delay_seconds(attempt))
                continue
            errors.append(f"request timed out: {exc}")
        except requests.exceptions.ConnectionError as exc:
            if attempt < MAX_RETRY_ATTEMPTS - 1 and should_retry_exception(exc):
                time.sleep(retry_delay_seconds(attempt))
                continue
            errors.append(f"connection failed: {exc}")
        except TimeoutError as exc:
            raise exc
        except requests.exceptions.RequestException as exc:
            status_code = exc.response.status_code if exc.response is not None else "unknown"
            details = {"status_code": status_code}
            if exc.response is not None and exc.response.text:
                details["raw_text"] = exc.response.text[:500]
            raise ToolError("SEMANTIC_SCHOLAR_REQUEST_FAILED", f"HTTP error: {exc}", details) from exc

    raise ToolError("SEMANTIC_SCHOLAR_REQUEST_FAILED", " ; ".join(errors) or "request failed after retries")


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    action = optional_string(request.get("action"), "action")
    if action != "call":
        raise ToolError("INVALID_REQUEST", "action must be call")

    endpoint = optional_string(request.get("endpoint"), "endpoint")
    endpoint = normalize_endpoint(endpoint)
    params = optional_object(request.get("params"), "params")
    payload = optional_object(request.get("payload"), "payload")
    options = optional_object(request.get("options"), "options")
    timeout_seconds = optional_int(
        options.get("timeout_seconds"),
        "options.timeout_seconds",
        DEFAULT_TIMEOUT_SECONDS,
        1,
        120,
    )

    validate_semantic_request(endpoint, params, payload)
    data = execute_semantic_scholar_call(endpoint, params, payload, timeout_seconds, resolve_s2_api_key())
    return {
        "ok": True,
        "action": action,
        "endpoint": endpoint,
        "method": resolve_endpoint_method(endpoint),
        "data": data,
        "meta": {
            "params": params,
            "payload": payload,
        },
    }


def write_json(value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    sys.stdout.buffer.write(payload.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main() -> int:
    try:
        write_json(handle_request(read_request()))
        return 0
    except ToolError as exc:
        error = {"code": exc.code, "message": str(exc)}
        if exc.details:
            error["details"] = exc.details
        write_json({"ok": False, "error": error})
        return 1
    except Exception as exc:
        write_json({"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
