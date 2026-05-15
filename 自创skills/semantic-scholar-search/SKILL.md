---
name: semantic-scholar-search
description: Query Semantic Scholar Academic Graph through a bundled agent-only JSON tool. Use when Codex needs stable Semantic Scholar paper search, paper detail lookup, citation/reference expansion, author lookup, author paper history, citation counts, influential citation counts, open-access PDF metadata, external IDs, or structured Semantic Scholar API output without shell-escaped JSON arguments.
---

# semantic-scholar-search

Use this skill only through the bundled tool contract:

```text
scripts/semantic_scholar_tool.py
```

Resolve the script relative to this skill directory, not relative to the current workspace. Send exactly one JSON request object to stdin. Read exactly one JSON response object from stdout. Do not pass JSON through command-line arguments.

The tool returns a uniform wrapper around Semantic Scholar responses. Treat a non-zero exit code or `"ok": false` as failure.

For endpoint-specific field and parameter details, read `references/semantic-scholar-api-reference.md` only when needed.

## API Key

The tool resolves `S2_API_KEY` in this order:

1. Process environment variable `S2_API_KEY`.
2. `scripts/.env`.

If the user provides a Semantic Scholar API key, write it through stdin:

```bash
printf '%s' "<api-key>" | python "<skill-dir>/scripts/set_s2_api_key.py"
```

Do not print or expose the key in final answers. Do not commit `scripts/.env`.

## Request Contract

All Semantic Scholar calls use the same request shape:

```json
{
  "action": "call",
  "endpoint": "paper/search",
  "params": {
    "query": "large language model reasoning",
    "limit": 10,
    "fields": "paperId,title,year,authors,citationCount,url"
  },
  "payload": {},
  "options": {
    "timeout_seconds": 20
  }
}
```

Fields:

- `action`: must be `call`.
- `endpoint`: Semantic Scholar Graph API endpoint path.
- `params`: query-string parameters as a JSON object. Optional, defaults to `{}`.
- `payload`: POST JSON body as a JSON object. Optional, defaults to `{}`.
- `options.timeout_seconds`: HTTP timeout from `1` to `120`. Optional, defaults to `20`.

Do not put JSON in command-line arguments. Do not use multiple invocation styles.

## Supported Endpoints

The tool supports these Graph API endpoint shapes:

- GET `paper/search`
- GET `paper/search/bulk`
- GET `paper/search/match`
- GET `paper/autocomplete`
- GET `snippet/search`
- GET `author/search`
- GET `paper/{paper_id}`
- GET `paper/{paper_id}/authors`
- GET `paper/{paper_id}/citations`
- GET `paper/{paper_id}/references`
- GET `author/{author_id}`
- GET `author/{author_id}/papers`
- POST `paper/batch`
- POST `author/batch`

For paper IDs that contain `/`, such as DOI IDs, pass the endpoint shape accepted by Semantic Scholar, for example `paper/DOI:10.1038/nrn3241`.

Known paper ID formats verified with this skill:

- `CorpusId:<id>` for Semantic Scholar corpus IDs.
- `DOI:<doi>` for DOI lookup.
- `ARXIV:<id>` for arXiv IDs when supported by the endpoint.

## Validation

The tool validates common Semantic Scholar limits before calling the API:

- `paper/search`: `params.limit <= 100` and `params.offset + params.limit < 1000`.
- `author/search`: `params.limit <= 1000` and `params.offset + params.limit < 10000`.
- `paper/{id}/authors`, `paper/{id}/references`, `paper/{id}/citations`, `author/{id}/papers`: `params.limit <= 1000`.
- `paper/batch`: `payload.ids` is required, all IDs must be non-empty strings, and at most 500 IDs are allowed.
- `author/batch`: `payload.ids` is required, all IDs must be non-empty strings, and at most 1000 IDs are allowed.
- Search-like endpoints require non-empty `params.query`.

If validation fails, fix the request and call the tool again. Do not bypass the tool with direct Semantic Scholar requests.

## Response Contract

Success response:

```json
{
  "ok": true,
  "action": "call",
  "endpoint": "paper/search",
  "method": "GET",
  "data": {
    "total": 1,
    "offset": 0,
    "data": []
  },
  "meta": {
    "params": {
      "query": "large language model reasoning",
      "limit": 10
    },
    "payload": {}
  }
}
```

The `data` field contains the parsed Semantic Scholar JSON response without reshaping.

Failure response:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_REQUEST",
    "message": "paper/search requires params.query"
  }
}
```

No results is a successful response when Semantic Scholar returns an empty result list.

Error codes:

- `INVALID_JSON`: stdin did not contain one valid JSON object.
- `INVALID_REQUEST`: request shape, endpoint, parameters, or payload violated the contract.
- `RATE_LIMIT_LOCK_TIMEOUT`: local cross-process pacing lock could not be acquired.
- `SEMANTIC_SCHOLAR_RATE_LIMITED`: Semantic Scholar returned 429 after retries.
- `SEMANTIC_SCHOLAR_REQUEST_FAILED`: Semantic Scholar request failed after retries or returned an HTTP error.
- `SEMANTIC_SCHOLAR_RESPONSE_INVALID`: Semantic Scholar returned non-JSON data.
- `INTERNAL_ERROR`: unexpected local tool failure.

## Invocation Pattern

Prefer direct subprocess stdin. If using a shell, pipe JSON to stdin and avoid inline JSON arguments.

PowerShell example:

```powershell
@'
{
  "action": "call",
  "endpoint": "paper/search",
  "params": {
    "query": "large language model reasoning",
    "limit": 10,
    "fields": "paperId,title,year,authors,citationCount,url"
  }
}
'@ | python "<skill-dir>\scripts\semantic_scholar_tool.py"
```

bash/zsh example:

```bash
cat <<'JSON' | python "<skill-dir>/scripts/semantic_scholar_tool.py"
{
  "action": "call",
  "endpoint": "paper/search",
  "params": {
    "query": "large language model reasoning",
    "limit": 10,
    "fields": "paperId,title,year,authors,citationCount,url"
  }
}
JSON
```

Replace `<skill-dir>` with the resolved path of this skill directory.

## Common Requests

Paper search:

```json
{
  "action": "call",
  "endpoint": "paper/search",
  "params": {
    "query": "large language model reasoning",
    "limit": 15,
    "offset": 0,
    "fields": "paperId,title,year,authors,abstract,citationCount,influentialCitationCount,venue,openAccessPdf,externalIds,url"
  }
}
```

Exact title match:

```json
{
  "action": "call",
  "endpoint": "paper/search/match",
  "params": {
    "query": "Attention Is All You Need",
    "fields": "paperId,title,authors,year,abstract,citationCount,openAccessPdf,externalIds,url,venue"
  }
}
```

Paper detail by known ID:

```json
{
  "action": "call",
  "endpoint": "paper/DOI:10.1038/nrn3241",
  "params": {
    "fields": "paperId,title,abstract,authors,year,citationCount,influentialCitationCount,openAccessPdf,externalIds,url,venue"
  }
}
```

Paper batch:

```json
{
  "action": "call",
  "endpoint": "paper/batch",
  "params": {
    "fields": "paperId,title,year,citationCount"
  },
  "payload": {
    "ids": ["649def34f8be52c8b66281af98ae884c09aef38b", "ARXIV:2106.15928"]
  }
}
```

Author search:

```json
{
  "action": "call",
  "endpoint": "author/search",
  "params": {
    "query": "Yoshua Bengio",
    "limit": 10,
    "offset": 0,
    "fields": "authorId,name,affiliations,paperCount,citationCount,hIndex,url"
  }
}
```

## Search Workflow

1. Identify whether the user needs paper search, exact title match, paper detail, citation expansion, reference expansion, author lookup, or author paper history.
2. Choose the narrowest endpoint that answers the question.
3. Request explicit `fields` for paper and author endpoints; do not rely on minimal default responses.
4. Keep `limit` modest and paginate only when needed.
5. Rank or filter results by relevance, year, citation count, and venue only when those fields are returned.
6. Use `openAccessPdf.url` only when present. Do not substitute paper pages, DOI pages, or Semantic Scholar pages as PDF links.
7. Before final output, verify that every title, author, citation count, URL, PDF URL, and external ID came from the tool response.

When presenting papers to the user, include title, authors, year, venue if returned, citation count if returned, influential citation count if returned, Semantic Scholar URL if returned, open-access PDF URL if returned, external IDs if useful, and a concise summary based only on `abstract` or `tldr` fields.
