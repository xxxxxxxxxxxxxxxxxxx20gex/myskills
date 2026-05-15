---
name: arxiv-search
description: Query arXiv through a bundled agent-only JSON tool. Use when Codex needs stable arXiv paper search, latest preprint lookup, exact arXiv ID retrieval, PDF URL extraction, category/date filtering, or structured arXiv API output without shell-escaped JSON arguments.
---

# arxiv-search

Use this skill only through the bundled tool contract:

```text
scripts/arxiv_tool.py
```

Resolve the script relative to this skill directory, not relative to the current workspace. Send exactly one JSON request object to stdin. Read exactly one JSON response object from stdout. Do not pass JSON through command-line arguments.

The tool writes diagnostics as structured JSON. Treat a non-zero exit code or `"ok": false` as failure.

## Request Contract

Search request:

```json
{
  "action": "search",
  "query": {
    "text": "retrieval augmented generation",
    "categories": ["cs.CL", "cs.AI"]
  },
  "options": {
    "max_results": 10,
    "sort_by": "submittedDate",
    "sort_order": "descending",
    "include_abstract": true,
    "include_pdf_url": true
  }
}
```

Exact paper lookup:

```json
{
  "action": "get_paper",
  "ids": ["2401.12345", "2409.09876v2"]
}
```

Supported actions:

- `search`: search with structured fields or an arXiv raw query.
- `get_paper`: retrieve exact arXiv IDs with `id` or `ids`.

## Query Fields

Use either `query.raw` or structured fields. Do not mix them.

Structured fields:

- `text`: maps to `all:"..."`.
- `title`: maps to `ti:"..."`.
- `author`: maps to `au:"..."`.
- `abstract`: maps to `abs:"..."`.
- `categories`: string array mapped to `cat:` terms joined with `OR`.
- `submitted_from` and `submitted_to`: both required together, using `YYYYMMDDHHMM`, mapped to `submittedDate:[from TO to]`.

Raw query:

```json
{
  "action": "search",
  "query": {
    "raw": "cat:cs.CL AND (all:retrieval OR all:reranking)"
  }
}
```

Useful arXiv query operators:

- `AND`
- `OR`
- `ANDNOT`
- quoted phrases
- parentheses for grouping

Common categories:

- `cs.CL`: computational linguistics / NLP
- `cs.CV`: computer vision
- `cs.LG`: machine learning
- `cs.AI`: artificial intelligence
- `cs.IR`: information retrieval
- `cs.RO`: robotics
- `stat.ML`: statistical machine learning

## Options

All options are optional:

- `start`: pagination offset. Default `0`.
- `max_results`: integer from `1` to `100`. Default `10`.
- `sort_by`: `relevance`, `submittedDate`, or `lastUpdatedDate`. Default `submittedDate`.
- `sort_order`: `ascending` or `descending`. Default `descending`.
- `include_abstract`: boolean. Default `true`.
- `include_pdf_url`: boolean. Default `true`.
- `timeout_seconds`: HTTP timeout from `1` to `120`. Default `15`.

Use `sort_by=submittedDate` and `sort_order=descending` for latest preprints. Keep `max_results` modest. Batch broad discovery into one query instead of making repeated calls.

## Response Contract

Success response:

```json
{
  "ok": true,
  "action": "search",
  "results": [
    {
      "id": "2401.12345",
      "title": "Paper title",
      "authors": ["A. Author"],
      "published": "2024-01-15",
      "updated": "2024-02-01",
      "primary_category": "cs.CL",
      "categories": ["cs.CL"],
      "paper_url": "https://arxiv.org/abs/2401.12345",
      "summary": "Abstract text",
      "pdf_url": "https://arxiv.org/pdf/2401.12345",
      "versioned_pdf_url": "https://arxiv.org/pdf/2401.12345v1",
      "doi": "missing",
      "journal_ref": "missing",
      "comment": "missing",
      "raw_entry_id": "http://arxiv.org/abs/2401.12345v1"
    }
  ],
  "meta": {
    "count": 1,
    "total_results": "1",
    "start_index": "0",
    "items_per_page": "1",
    "api_params": {
      "search_query": "all:\"retrieval augmented generation\"",
      "start": "0",
      "max_results": "10",
      "sortBy": "submittedDate",
      "sortOrder": "descending"
    }
  }
}
```

Failure response:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "query.raw cannot be combined with structured query fields"
  }
}
```

No results is a successful response with an empty `results` array.

Error codes:

- `INVALID_JSON`: stdin did not contain one valid JSON object.
- `INVALID_REQUEST`: request shape or field values violated the contract.
- `RATE_LIMIT_LOCK_TIMEOUT`: local cross-process arXiv pacing lock could not be acquired.
- `ARXIV_REQUEST_FAILED`: arXiv API request failed after retries.
- `ARXIV_RESPONSE_INVALID`: arXiv returned XML that could not be parsed.
- `INTERNAL_ERROR`: unexpected local tool failure.

## Invocation Pattern

Prefer direct subprocess stdin. If using a shell, pipe JSON to stdin and avoid inline JSON arguments.

PowerShell example:

```powershell
@'
{
  "action": "search",
  "query": {
    "text": "retrieval augmented generation",
    "categories": ["cs.CL"]
  },
  "options": {
    "max_results": 5
  }
}
'@ | python "<skill-dir>\scripts\arxiv_tool.py"
```

bash/zsh example:

```bash
cat <<'JSON' | python "<skill-dir>/scripts/arxiv_tool.py"
{
  "action": "search",
  "query": {
    "text": "retrieval augmented generation",
    "categories": ["cs.CL"]
  },
  "options": {
    "max_results": 5
  }
}
JSON
```

Replace `<skill-dir>` with the resolved path of this skill directory.

## Search Workflow

1. Parse the user's request into topic, category, author, date range, target result count, and sort preference.
2. Use `get_paper` when arXiv IDs are known.
3. Use one `search` request with structured fields for ordinary search.
4. Use `query.raw` only when arXiv query syntax is needed.
5. Request enough results for the task, usually `10` to `50`.
6. If results are too broad, add category, title, author, abstract, or submitted date filters.
7. If results are too few, relax category/date constraints or broaden query terms.
8. Before final output, verify that every cited title, URL, PDF URL, date, and category came from the tool response.

When presenting papers to the user, include title, authors, arXiv ID, publication/update date, category, paper URL, PDF URL if present, and a concise summary based only on `summary`. Do not infer citation counts, journal venues, or metadata that is not present in the response.
