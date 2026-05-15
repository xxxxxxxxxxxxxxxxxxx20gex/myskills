#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime
from typing import Any

ARXIV_API_URL = "https://export.arxiv.org/api/query"
RATE_LIMIT_SECONDS = 3.1
DEFAULT_HTTP_TIMEOUT_SECONDS = 15
LOCK_WAIT_TIMEOUT_SECONDS = 120
STALE_LOCK_SECONDS = 160
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRY_BACKOFF_MAX_SECONDS = 8.0
RETRY_BACKOFF_JITTER_SECONDS = 0.25
MISSING_VALUE = "missing"
ARXIV_XML_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}
SORT_BY_VALUES = {"relevance", "submittedDate", "lastUpdatedDate"}
SORT_ORDER_VALUES = {"ascending", "descending"}


class ToolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@contextmanager
def arxiv_rate_limit_lock():
    state_dir = os.path.join(tempfile.gettempdir(), "arxiv-search-skill")
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
                raise ToolError("RATE_LIMIT_LOCK_TIMEOUT", "Timed out waiting for the local arXiv rate-limit lock")
            if time.time() - os.path.getmtime(lock_path) > STALE_LOCK_SECONDS:
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


def optional_bool(value: Any, path: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ToolError("INVALID_REQUEST", f"{path} must be a boolean")
    return value


def optional_int(value: Any, path: str, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise ToolError("INVALID_REQUEST", f"{path} must be an integer")
    if value < minimum or value > maximum:
        raise ToolError("INVALID_REQUEST", f"{path} must be between {minimum} and {maximum}")
    return value


def optional_string_list(value: Any, path: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ToolError("INVALID_REQUEST", f"{path} must be an array of strings")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ToolError("INVALID_REQUEST", f"{path}[{index}] must be a non-empty string")
        result.append(item.strip())
    return result


def option_enum(value: Any, path: str, default: str, allowed: set[str]) -> str:
    if value is None:
        return default
    if not isinstance(value, str) or value not in allowed:
        allowed_values = ", ".join(sorted(allowed))
        raise ToolError("INVALID_REQUEST", f"{path} must be one of: {allowed_values}")
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


def normalize_options(raw_options: dict[str, Any]) -> dict[str, Any]:
    return {
        "start": optional_int(raw_options.get("start"), "options.start", 0, 0, 100000),
        "max_results": optional_int(raw_options.get("max_results"), "options.max_results", 10, 1, 100),
        "sort_by": option_enum(raw_options.get("sort_by"), "options.sort_by", "submittedDate", SORT_BY_VALUES),
        "sort_order": option_enum(raw_options.get("sort_order"), "options.sort_order", "descending", SORT_ORDER_VALUES),
        "include_abstract": optional_bool(raw_options.get("include_abstract"), "options.include_abstract", True),
        "include_pdf_url": optional_bool(raw_options.get("include_pdf_url"), "options.include_pdf_url", True),
        "timeout_seconds": optional_int(
            raw_options.get("timeout_seconds"),
            "options.timeout_seconds",
            DEFAULT_HTTP_TIMEOUT_SECONDS,
            1,
            120,
        ),
    }


def arxiv_phrase(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_search_query(raw_query: dict[str, Any]) -> str:
    raw = optional_string(raw_query.get("raw"), "query.raw")
    structured_keys = ("text", "title", "author", "abstract", "categories", "submitted_from", "submitted_to")
    structured_present = any(raw_query.get(key) not in (None, [], "") for key in structured_keys)
    if raw and structured_present:
        raise ToolError("INVALID_REQUEST", "query.raw cannot be combined with structured query fields")
    if raw:
        return raw

    parts = []
    text = optional_string(raw_query.get("text"), "query.text")
    title = optional_string(raw_query.get("title"), "query.title")
    author = optional_string(raw_query.get("author"), "query.author")
    abstract = optional_string(raw_query.get("abstract"), "query.abstract")
    categories = optional_string_list(raw_query.get("categories"), "query.categories")
    submitted_from = optional_string(raw_query.get("submitted_from"), "query.submitted_from")
    submitted_to = optional_string(raw_query.get("submitted_to"), "query.submitted_to")

    if text:
        parts.append(f"all:{arxiv_phrase(text)}")
    if title:
        parts.append(f"ti:{arxiv_phrase(title)}")
    if author:
        parts.append(f"au:{arxiv_phrase(author)}")
    if abstract:
        parts.append(f"abs:{arxiv_phrase(abstract)}")
    if categories:
        category_query = " OR ".join(f"cat:{category}" for category in categories)
        parts.append(f"({category_query})" if len(categories) > 1 else category_query)
    if submitted_from or submitted_to:
        if not submitted_from or not submitted_to:
            raise ToolError("INVALID_REQUEST", "query.submitted_from and query.submitted_to must be provided together")
        if not re.fullmatch(r"\d{12}", submitted_from) or not re.fullmatch(r"\d{12}", submitted_to):
            raise ToolError("INVALID_REQUEST", "submitted date bounds must use YYYYMMDDHHMM")
        parts.append(f"submittedDate:[{submitted_from} TO {submitted_to}]")

    if not parts:
        raise ToolError(
            "INVALID_REQUEST",
            "query must include raw, text, title, author, abstract, categories, or submitted date bounds",
        )
    return " AND ".join(parts)


def build_api_params(request: dict[str, Any], options: dict[str, Any]) -> dict[str, str]:
    action = optional_string(request.get("action"), "action")
    if action == "search":
        query = require_object(request.get("query"), "query")
        return {
            "search_query": build_search_query(query),
            "start": str(options["start"]),
            "max_results": str(options["max_results"]),
            "sortBy": options["sort_by"],
            "sortOrder": options["sort_order"],
        }
    if action == "get_paper":
        ids = optional_string_list(request.get("ids"), "ids")
        single_id = optional_string(request.get("id"), "id")
        if single_id:
            ids.insert(0, single_id)
        if not ids:
            raise ToolError("INVALID_REQUEST", "get_paper requires id or ids")
        return {
            "id_list": ",".join(ids),
            "start": str(options["start"]),
            "max_results": str(min(options["max_results"], len(ids))),
        }
    raise ToolError("INVALID_REQUEST", "action must be search or get_paper")


def xml_text_or_missing(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return MISSING_VALUE
    text = element.text.strip()
    return text if text else MISSING_VALUE


def extract_arxiv_id(raw_entry_id: str) -> str:
    if raw_entry_id == MISSING_VALUE:
        return MISSING_VALUE
    if "arxiv.org/abs/" in raw_entry_id:
        return raw_entry_id.split("arxiv.org/abs/")[-1].rstrip("/")
    return raw_entry_id


def strip_arxiv_version(arxiv_id: str) -> str:
    if arxiv_id == MISSING_VALUE:
        return MISSING_VALUE
    return re.sub(r"v\d+$", "", arxiv_id.strip())


def build_arxiv_abs_url(arxiv_id: str) -> str:
    canonical_id = strip_arxiv_version(arxiv_id)
    if canonical_id == MISSING_VALUE:
        return MISSING_VALUE
    return f"https://arxiv.org/abs/{canonical_id}"


def build_arxiv_pdf_url(arxiv_id: str) -> str:
    canonical_id = strip_arxiv_version(arxiv_id)
    if canonical_id == MISSING_VALUE:
        return MISSING_VALUE
    return f"https://arxiv.org/pdf/{canonical_id}"


def normalize_date(value: str) -> str:
    if not value or value == MISSING_VALUE:
        return MISSING_VALUE
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return value[:10]


def parse_arxiv_feed(feed_text: str, include_abstract: bool, include_pdf_url: bool) -> dict[str, Any]:
    try:
        root = ET.fromstring(feed_text)
    except ET.ParseError as exc:
        raise ToolError("ARXIV_RESPONSE_INVALID", f"arXiv returned invalid XML: {exc}") from exc

    results = []
    for entry in root.findall("atom:entry", ARXIV_XML_NS):
        raw_entry_id = xml_text_or_missing(entry.find("atom:id", ARXIV_XML_NS))
        arxiv_id = extract_arxiv_id(raw_entry_id)

        primary_category = MISSING_VALUE
        primary_category_elem = entry.find("arxiv:primary_category", ARXIV_XML_NS)
        if primary_category_elem is not None:
            primary_category = (primary_category_elem.get("term") or "").strip() or MISSING_VALUE

        categories = []
        for tag in entry.findall("atom:category", ARXIV_XML_NS):
            term = (tag.get("term") or "").strip()
            if term:
                categories.append(term)
        if primary_category == MISSING_VALUE and categories:
            primary_category = categories[0]

        versioned_pdf_url = MISSING_VALUE
        for link in entry.findall("atom:link", ARXIV_XML_NS):
            href = (link.get("href") or "").strip()
            link_type = (link.get("type") or "").strip()
            link_title = (link.get("title") or "").strip().lower()
            if href and (link_type == "application/pdf" or link_title == "pdf"):
                versioned_pdf_url = href
                break

        result = {
            "id": arxiv_id,
            "title": xml_text_or_missing(entry.find("atom:title", ARXIV_XML_NS)),
            "authors": [
                author_name
                for author_name in (
                    xml_text_or_missing(author.find("atom:name", ARXIV_XML_NS))
                    for author in entry.findall("atom:author", ARXIV_XML_NS)
                )
                if author_name != MISSING_VALUE
            ],
            "published": normalize_date(xml_text_or_missing(entry.find("atom:published", ARXIV_XML_NS))),
            "updated": normalize_date(xml_text_or_missing(entry.find("atom:updated", ARXIV_XML_NS))),
            "primary_category": primary_category,
            "categories": categories,
            "paper_url": build_arxiv_abs_url(arxiv_id),
            "doi": xml_text_or_missing(entry.find("arxiv:doi", ARXIV_XML_NS)),
            "journal_ref": xml_text_or_missing(entry.find("arxiv:journal_ref", ARXIV_XML_NS)),
            "comment": xml_text_or_missing(entry.find("arxiv:comment", ARXIV_XML_NS)),
            "raw_entry_id": raw_entry_id,
        }
        if include_abstract:
            result["summary"] = xml_text_or_missing(entry.find("atom:summary", ARXIV_XML_NS))
        if include_pdf_url:
            result["pdf_url"] = build_arxiv_pdf_url(arxiv_id) if versioned_pdf_url != MISSING_VALUE else MISSING_VALUE
            result["versioned_pdf_url"] = versioned_pdf_url
        results.append(result)

    return {
        "title": xml_text_or_missing(root.find("atom:title", ARXIV_XML_NS)),
        "updated": xml_text_or_missing(root.find("atom:updated", ARXIV_XML_NS)),
        "total_results": xml_text_or_missing(root.find("opensearch:totalResults", ARXIV_XML_NS)),
        "start_index": xml_text_or_missing(root.find("opensearch:startIndex", ARXIV_XML_NS)),
        "items_per_page": xml_text_or_missing(root.find("opensearch:itemsPerPage", ARXIV_XML_NS)),
        "count": len(results),
        "results": results,
    }


def retry_delay_seconds(attempt: int, retry_after: str | None = None) -> float:
    delay = min(RETRY_BACKOFF_MAX_SECONDS, RETRY_BACKOFF_BASE_SECONDS * (2**attempt))
    if retry_after:
        try:
            delay = max(delay, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return delay + random.uniform(0, RETRY_BACKOFF_JITTER_SECONDS)


def fetch_arxiv(params: dict[str, str], timeout_seconds: int) -> str:
    encoded_params = urllib.parse.urlencode(params)
    url = f"{ARXIV_API_URL}?{encoded_params}"
    errors = []

    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            with arxiv_rate_limit_lock():
                request = urllib.request.Request(url, headers={"User-Agent": "codex-arxiv-search-skill/1.0"})
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in RETRY_STATUS_CODES and attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(retry_delay_seconds(attempt, exc.headers.get("Retry-After")))
                continue
            errors.append(f"HTTP {exc.code}: {exc.reason}")
        except urllib.error.URLError as exc:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(retry_delay_seconds(attempt))
                continue
            errors.append(f"URL error: {exc.reason}")
        except TimeoutError as exc:
            raise exc
        except OSError as exc:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(retry_delay_seconds(attempt))
                continue
            errors.append(f"I/O error: {exc}")

    raise ToolError("ARXIV_REQUEST_FAILED", " ; ".join(errors) or "arXiv request failed")


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    action = optional_string(request.get("action"), "action")
    options = normalize_options(optional_object(request.get("options"), "options"))
    params = build_api_params(request, options)
    feed = fetch_arxiv(params, options["timeout_seconds"])
    parsed = parse_arxiv_feed(feed, options["include_abstract"], options["include_pdf_url"])
    return {
        "ok": True,
        "action": action,
        "results": parsed.pop("results"),
        "meta": {
            **parsed,
            "api_params": params,
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
        write_json({"ok": False, "error": {"code": exc.code, "message": str(exc)}})
        return 1
    except Exception as exc:
        write_json({"ok": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
