# arxiv-search Skill Test Report

Date: 2026-05-13

Branch: `arxiv-agent-tool-protocol`

Head commit at test time: `a5ccc2a refactor arxiv skill to agent json protocol`

## Summary

Result: PASS

Total checks: 13

Passed: 13

Failed: 0

Scope:

- Python syntax/compile checks.
- Skill metadata/frontmatter validation.
- Agent tool protocol error handling.
- arXiv query validation.
- Live arXiv API functionality.
- Light concurrency/rate-limit smoke test.

## Environment

- Workspace: `C:\Users\23262\.codex\skills\arxiv-search`
- Python: `3.12.7`
- Tool under test: `scripts/arxiv_tool.py`
- Network: enabled; live requests were sent to `https://export.arxiv.org/api/query`.

Ignored local files during testing:

- `scripts/__pycache__/`

## Test Matrix

| Area | Case | Expected | Result |
| --- | --- | --- | --- |
| Static | `py_compile` for `arxiv_tool.py` | Exit 0 | PASS |
| Skill validation | `quick_validate.py` | `Skill is valid!` | PASS |
| Protocol | Empty stdin | `ok=false`, `INVALID_JSON`, non-zero exit | PASS |
| Protocol | Malformed JSON | `ok=false`, `INVALID_JSON`, non-zero exit | PASS |
| Request validation | `query.raw` mixed with structured fields | `ok=false`, `INVALID_REQUEST` | PASS |
| Request validation | Empty search query object | `ok=false`, `INVALID_REQUEST` | PASS |
| Request validation | Invalid `options.sort_by` | `ok=false`, `INVALID_REQUEST` | PASS |
| Request validation | One-sided submitted date bound | `ok=false`, `INVALID_REQUEST` | PASS |
| Live API | Structured search for `retrieval augmented generation` in `cs.CL` | `ok=true`, one returned paper | PASS |
| Live API | Raw arXiv query `cat:cs.CL AND all:retrieval` | `ok=true`, one returned paper | PASS |
| Live API | Exact paper lookup for `1706.03762` | `ok=true`, `Attention Is All You Need` returned | PASS |
| Live API | Submitted date range search | `ok=true`, response parsed successfully | PASS |
| Stress smoke | 3 concurrent structured search calls | All calls succeed under local rate-limit lock | PASS |

## Live API Evidence

Structured search returned one result for `retrieval augmented generation` in `cs.CL`:

- arXiv ID: `2605.12313v1`
- Title: `Overview of the MedHopQA track at BioCreative IX: track description, participation and evaluation of systems for multi-hop medical question answering`
- Published: `2026-05-12`
- Primary category: `cs.CL`

Raw search returned one result for `cat:cs.CL AND all:retrieval`:

- arXiv ID: `2605.12487v1`
- Title: `Task-Adaptive Embedding Refinement via Test-time LLM Guidance`
- Published: `2026-05-12`

Exact paper lookup for `1706.03762` returned:

- arXiv ID: `1706.03762v7`
- Title: `Attention Is All You Need`
- Published: `2017-06-12`
- Updated: `2023-08-02`
- Categories: `cs.CL`, `cs.LG`

Submitted date range search returned a parsed `ok=true` response with one result.

## Stress Smoke

The concurrency smoke test launched 3 simultaneous structured search tool processes. All 3 calls returned `ok=true`.

Observed elapsed time for the concurrent group: approximately `9.636` seconds.

This is consistent with the tool's local cross-process arXiv pacing lock and `3.1` second minimum interval between request starts. The test confirms the lock does not deadlock under light concurrent use. This was not a high-volume load test.

## Regressions Covered

The run specifically covered the regressions that motivated the refactor:

- No JSON is passed through command-line arguments.
- Empty or malformed stdin returns structured JSON errors.
- Invalid request shapes return structured JSON errors.
- `query.raw` cannot be mixed with structured query fields.
- Invalid sort values are rejected before network calls.
- Submitted date bounds must be provided together and use the expected shape.
- Success and failure responses are uniform JSON objects.
- Windows console encoding is avoided by writing UTF-8 bytes to stdout.
- XML parsing from the live arXiv Atom feed returns normalized result fields.

## Residual Risk

- Live arXiv results are time-sensitive and can change.
- The concurrency check is a smoke test only. It does not prove behavior under sustained high concurrency.
- Tests intentionally kept `max_results=1` to avoid unnecessary API load.
- The test did not cover every possible arXiv query prefix or malformed raw arXiv query.
- arXiv service availability and rate-limit behavior can vary over time.

## Conclusion

The arxiv-search skill passed protocol, validation, live functionality, and light concurrency regression testing. The current agent-only stdin JSON to stdout JSON contract is working, and the local rate-limit lock behaved correctly during the smoke test.
