#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import random
import re
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_SEARCH_URL = "https://arxiv.org/search/"
RATE_LIMIT_SECONDS = 3.1
DEFAULT_HTTP_TIMEOUT_SECONDS = 15
LOCK_WAIT_TIMEOUT_SECONDS = 120
STALE_LOCK_SECONDS = 160
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRY_BACKOFF_MAX_SECONDS = 8.0
RETRY_BACKOFF_JITTER_SECONDS = 0.25
RATE_LIMIT_HTTP_COOLDOWN_SECONDS = 60.0
RATE_LIMIT_HTTP_STATE_TTL_SECONDS = 300
MISSING_VALUE = "missing"
ARXIV_XML_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}
SORT_BY_VALUES = {"relevance", "submittedDate", "lastUpdatedDate"}
SORT_ORDER_VALUES = {"ascending", "descending"}
SEARCH_PAGE_SIZE_VALUES = (25, 50, 100, 200)
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) codex-arxiv-search-skill/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


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
            if time.time() - os.path.getmtime(lock_path) > STALE_LOCK_SECONDS:
                try:
                    os.rmdir(lock_path)
                except OSError:
                    pass
                continue
            if time.monotonic() - lock_wait_started > LOCK_WAIT_TIMEOUT_SECONDS:
                raise ToolError("RATE_LIMIT_LOCK_TIMEOUT", "Timed out waiting for the local arXiv rate-limit lock")
            time.sleep(0.2)

    try:
        if os.path.exists(state_path):
            with open(state_path, "r", encoding="utf-8") as state_file:
                last_request_at = float(json.load(state_file).get("last_request_at", 0))
            elapsed_seconds = time.monotonic() - last_request_at
            wait_seconds = RATE_LIMIT_SECONDS - elapsed_seconds if elapsed_seconds >= 0 else 0
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


def search_page_size(max_results: int) -> int:
    for size in SEARCH_PAGE_SIZE_VALUES:
        if max_results <= size:
            return size
    return SEARCH_PAGE_SIZE_VALUES[-1]


def search_page_order(sort_by: str, sort_order: str) -> str | None:
    if sort_by == "relevance":
        return None
    if sort_by == "lastUpdatedDate":
        return "-announced_date_first" if sort_order == "descending" else "announced_date_first"
    return "-announced_date_first" if sort_order == "descending" else "announced_date_first"


def search_page_query(params: dict[str, str]) -> str:
    query = params["search_query"]
    query = re.sub(r"submittedDate:\[[^\]]+\]", " ", query)
    query = re.sub(r"\bcat:[A-Za-z0-9.]+", " ", query)
    query = re.sub(r"\b(all|ti|au|abs):", "", query)
    query = re.sub(r"\b(ANDNOT|AND|OR)\b", " ", query)
    query = query.replace('"', " ").replace("(", " ").replace(")", " ")
    return " ".join(query.split())


def search_page_categories(params: dict[str, str]) -> set[str]:
    return set(re.findall(r"\bcat:([A-Za-z0-9.]+)", params["search_query"]))


def parse_search_page_date(value: str) -> str:
    match = re.search(r"Submitted\s+([^;]+)", value)
    if not match:
        return MISSING_VALUE
    raw_date = match.group(1).strip()
    for pattern in ("%d %B, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw_date, pattern).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return raw_date


class ArxivSearchPageParser(HTMLParser):
    def __init__(self, include_abstract: bool, include_pdf_url: bool):
        super().__init__(convert_charrefs=True)
        self.include_abstract = include_abstract
        self.include_pdf_url = include_pdf_url
        self.results: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.depth = 0
        self.link_text = False
        self.link_href = ""
        self.in_title = False
        self.in_authors = False
        self.in_abstract = False
        self.abstract_depth = 0
        self.in_submitted = False
        self.submitted_depth = 0
        self.in_tag = False
        self.text_buffer: list[str] = []
        self.author_buffer: list[str] = []
        self.abstract_buffer: list[str] = []
        self.submitted_buffer: list[str] = []
        self.tag_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = attr.get("class", "").split()
        if self.current is None and tag == "li" and "arxiv-result" in classes:
            self.current = {
                "id": MISSING_VALUE,
                "title": MISSING_VALUE,
                "authors": [],
                "published": MISSING_VALUE,
                "updated": MISSING_VALUE,
                "primary_category": MISSING_VALUE,
                "categories": [],
                "paper_url": MISSING_VALUE,
                "doi": MISSING_VALUE,
                "journal_ref": MISSING_VALUE,
                "comment": MISSING_VALUE,
                "raw_entry_id": MISSING_VALUE,
            }
            if self.include_abstract:
                self.current["summary"] = MISSING_VALUE
            if self.include_pdf_url:
                self.current["pdf_url"] = MISSING_VALUE
                self.current["versioned_pdf_url"] = MISSING_VALUE
            self.depth = 1
            return
        if self.current is None:
            return

        self.depth += 1
        if tag == "a":
            href = attr.get("href", "")
            if "/abs/" in href or "/pdf/" in href:
                self.link_text = True
                self.link_href = href
                self.text_buffer = []
            if self.in_authors:
                self.author_buffer = []
        if tag == "p" and "title" in classes:
            self.in_title = True
            self.text_buffer = []
        if tag == "p" and "authors" in classes:
            self.in_authors = True
        if tag == "span" and "abstract-full" in classes and attr.get("id", "").endswith("-abstract-full"):
            self.in_abstract = True
            self.abstract_depth = 1
            self.abstract_buffer = []
        elif self.in_abstract and tag == "span":
            self.abstract_depth += 1
        if tag == "p" and "is-size-7" in classes:
            self.in_submitted = True
            self.submitted_depth = 1
            self.submitted_buffer = []
        elif self.in_submitted:
            self.submitted_depth += 1
        if tag == "span" and "tag" in classes:
            self.in_tag = True
            self.tag_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if self.link_text and tag == "a":
            href = self.link_href
            if "/abs/" in href:
                arxiv_id = href.rsplit("/abs/", 1)[-1].strip("/")
                self.current["id"] = arxiv_id
                self.current["paper_url"] = build_arxiv_abs_url(arxiv_id)
                self.current["raw_entry_id"] = f"http://arxiv.org/abs/{arxiv_id}"
            elif self.include_pdf_url and "/pdf/" in href:
                arxiv_id = href.rsplit("/pdf/", 1)[-1].strip("/")
                self.current["pdf_url"] = build_arxiv_pdf_url(arxiv_id)
                self.current["versioned_pdf_url"] = f"https://arxiv.org/pdf/{arxiv_id}"
            self.link_text = False
            self.link_href = ""
            self.text_buffer = []
        if self.in_title and tag == "p":
            self.current["title"] = " ".join("".join(self.text_buffer).split()) or MISSING_VALUE
            self.in_title = False
            self.text_buffer = []
        if self.in_authors and tag == "a":
            author = " ".join("".join(self.author_buffer).split())
            if author:
                self.current["authors"].append(author)
            self.author_buffer = []
        if self.in_authors and tag == "p":
            self.in_authors = False
        if self.in_abstract and tag == "span":
            self.abstract_depth -= 1
        if self.in_abstract and self.abstract_depth == 0:
            summary = " ".join("".join(self.abstract_buffer).split())
            summary = re.sub(r"^Abstract\s*:\s*", "", summary)
            summary = re.sub(r"\s*[△▽]\s*(Less|More)\s*$", "", summary)
            if summary:
                self.current["summary"] = summary
            self.in_abstract = False
            self.abstract_depth = 0
        if self.in_submitted:
            self.submitted_depth -= 1
        if self.in_submitted and self.submitted_depth == 0:
            submitted = " ".join("".join(self.submitted_buffer).split())
            if "Submitted" in submitted:
                self.current["published"] = parse_search_page_date(submitted)
            self.in_submitted = False
            self.submitted_depth = 0
        if self.in_tag and tag == "span":
            category = "".join(self.tag_buffer).strip()
            if re.fullmatch(r"[a-z]{2,}(?:\.[A-Z]{2,})?", category):
                self.current["categories"].append(category)
                if self.current["primary_category"] == MISSING_VALUE:
                    self.current["primary_category"] = category
            self.in_tag = False

        self.depth -= 1
        if tag == "li" and self.depth == 0:
            self.results.append(self.current)
            self.current = None

    def handle_data(self, data: str) -> None:
        if self.current is None:
            return
        if self.link_text or self.in_title:
            self.text_buffer.append(data)
        if self.in_authors:
            self.author_buffer.append(data)
        if self.in_abstract:
            self.abstract_buffer.append(data)
        if self.in_submitted:
            self.submitted_buffer.append(data)
        if self.in_tag:
            self.tag_buffer.append(data)


def parse_arxiv_search_page(
    page_text: str,
    include_abstract: bool,
    include_pdf_url: bool,
    max_results: int,
    categories: set[str],
) -> dict[str, Any]:
    parser = ArxivSearchPageParser(include_abstract, include_pdf_url)
    parser.feed(page_text)
    results = parser.results
    if categories:
        results = [result for result in results if categories.intersection(result["categories"])]
    return {
        "title": "arXiv Search",
        "updated": MISSING_VALUE,
        "total_results": MISSING_VALUE,
        "start_index": MISSING_VALUE,
        "items_per_page": str(search_page_size(max_results)),
        "count": min(len(results), max_results),
        "results": results[:max_results],
    }


def fetch_arxiv_search_page(params: dict[str, str], options: dict[str, Any]) -> str:
    if "search_query" not in params or int(params["start"]) != 0:
        raise ToolError("ARXIV_REQUEST_FAILED", "arXiv API request failed and search-page fallback cannot handle this request")
    page_params = {
        "query": search_page_query(params),
        "searchtype": "all",
        "abstracts": "show" if options["include_abstract"] else "hide",
        "size": str(search_page_size(options["max_results"])),
    }
    order = search_page_order(options["sort_by"], options["sort_order"])
    if order:
        page_params["order"] = order
    url = f"{ARXIV_SEARCH_URL}?{urllib.parse.urlencode(page_params)}"
    request = urllib.request.Request(url, headers=REQUEST_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=options["timeout_seconds"]) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ToolError("ARXIV_REQUEST_FAILED", f"arXiv search page fallback failed with HTTP {exc.code}: {exc.reason}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        raise ToolError("ARXIV_REQUEST_FAILED", f"arXiv search page fallback failed: {exc}") from exc


def retry_delay_seconds(attempt: int, retry_after: str | None = None) -> float:
    delay = min(RETRY_BACKOFF_MAX_SECONDS, RETRY_BACKOFF_BASE_SECONDS * (2**attempt))
    if retry_after:
        try:
            delay = max(delay, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return delay + random.uniform(0, RETRY_BACKOFF_JITTER_SECONDS)


def rate_limit_state_path() -> str:
    state_dir = os.path.join(tempfile.gettempdir(), "arxiv-search-skill")
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "http-429-until.json")


def read_http_rate_limit_until() -> float:
    state_path = rate_limit_state_path()
    if not os.path.exists(state_path):
        return 0.0
    try:
        if time.time() - os.path.getmtime(state_path) > RATE_LIMIT_HTTP_STATE_TTL_SECONDS:
            return 0.0
        with open(state_path, "r", encoding="utf-8") as state_file:
            retry_after_monotonic = float(json.load(state_file).get("retry_after_monotonic", 0))
        return min(retry_after_monotonic, time.monotonic() + RATE_LIMIT_HTTP_COOLDOWN_SECONDS)
    except (OSError, ValueError, json.JSONDecodeError):
        return 0.0


def write_http_rate_limit_until(retry_after_seconds: float) -> None:
    with open(rate_limit_state_path(), "w", encoding="utf-8") as state_file:
        json.dump({"retry_after_monotonic": time.monotonic() + retry_after_seconds}, state_file)


def http_429_delay_seconds(retry_after: str | None = None) -> float:
    if retry_after:
        try:
            return max(RATE_LIMIT_HTTP_COOLDOWN_SECONDS, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return RATE_LIMIT_HTTP_COOLDOWN_SECONDS


def fetch_arxiv(params: dict[str, str], timeout_seconds: int) -> str:
    encoded_params = urllib.parse.urlencode(params)
    url = f"{ARXIV_API_URL}?{encoded_params}"
    errors = []

    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            retry_after_monotonic = read_http_rate_limit_until()
            wait_seconds = retry_after_monotonic - time.monotonic()
            if wait_seconds > 0:
                raise ToolError(
                    "ARXIV_RATE_LIMITED",
                    f"arXiv rate limit cooldown is active; retry after about {int(wait_seconds) + 1} seconds",
                )
            with arxiv_rate_limit_lock():
                request = urllib.request.Request(url, headers=REQUEST_HEADERS)
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                delay = http_429_delay_seconds(exc.headers.get("Retry-After"))
                write_http_rate_limit_until(delay)
                errors.append(f"HTTP 429: rate exceeded; retry after about {int(delay)} seconds")
                break
            if exc.code in RETRY_STATUS_CODES and attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(retry_delay_seconds(attempt, exc.headers.get("Retry-After")))
                continue
            errors.append(f"HTTP {exc.code}: {exc.reason}")
        except urllib.error.URLError as exc:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(retry_delay_seconds(attempt))
                continue
            errors.append(f"URL error: {exc.reason}")
        except (TimeoutError, socket.timeout) as exc:
            if attempt < MAX_RETRY_ATTEMPTS - 1:
                time.sleep(retry_delay_seconds(attempt))
                continue
            errors.append(f"Timeout: {exc}")
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
    source = "export_api"
    try:
        feed = fetch_arxiv(params, options["timeout_seconds"])
        parsed = parse_arxiv_feed(feed, options["include_abstract"], options["include_pdf_url"])
    except ToolError:
        if action != "search":
            raise
        source = "search_page_fallback"
        page = fetch_arxiv_search_page(params, options)
        parsed = parse_arxiv_search_page(
            page,
            options["include_abstract"],
            options["include_pdf_url"],
            options["max_results"],
            search_page_categories(params),
        )
    return {
        "ok": True,
        "action": action,
        "results": parsed.pop("results"),
        "meta": {
            **parsed,
            "api_params": params,
            "source": source,
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
