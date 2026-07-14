---
name: mineru-to-markdown
description: Convert documents to Markdown with the MinerU cloud API. Use when Codex needs to parse, OCR, or extract Markdown from local files or URLs, including PDF, DOC/DOCX, PPT/PPTX, images, Excel files, or HTML via MinerU Precision mode.
---

# MinerU To Markdown

Use `scripts/convert.py` for MinerU API conversion instead of rewriting HTTP polling code.

## Quick Start

By default, the script reads `MINERU_API_TOKEN` from `mineru-to-markdown/.env` first. If a token exists, it uses Precision mode; otherwise, it falls back to Agent Lightweight mode.

Default output creates one exportable folder per source file when `--out` is omitted:

```text
mineru-to-markdown/workspace/<source-name>/<source-name>.md
mineru-to-markdown/workspace/<source-name>/images/
```

```powershell
python C:\Users\23262\.codex\skills\mineru-to-markdown\scripts\convert.py "C:\path\paper.pdf"
python C:\Users\23262\.codex\skills\mineru-to-markdown\scripts\convert.py "https://example.com/paper.pdf"
```

Create `mineru-to-markdown/.env` from `.env.example` to enable token-backed Precision mode:

```powershell
MINERU_API_TOKEN=...
```

Pass `--out` only when the user asks for a specific destination. When Markdown contains `images/...` references, keep the Markdown and its `images/` folder together.

## Mode Selection

- Auto mode is the default: `MINERU_API_TOKEN` or `--token` selects Precision mode; no token selects Agent Lightweight mode.
- Agent Lightweight mode needs no token, returns Markdown only, and is limited to small single files.
- Precision mode needs `MINERU_API_TOKEN` from `.env` or `--token`, returns a result ZIP, and this script extracts `full.md`.
- If Precision mode fails on a local file during the MinerU upload/service path (for example `SignatureDoesNotMatch` or HTTP 5xx), the converter automatically falls back to Agent Lightweight mode and prints `FLASH_FALLBACK_USED=true`.
- For HTML input, use `--mode precision --model MinerU-HTML`.
- For scanned PDFs, pass `--ocr`.
- For page subsets, pass `--pages`, for example `--pages 1-10`.

## Verification

After conversion, open or inspect the generated Markdown. If `FLASH_FALLBACK_USED=true` appears, the final response MUST explicitly state that a degraded flash/Agent fallback was used, why Precision mode failed, and that table, formula, OCR, and complex-layout fidelity may be lower. Report image/asset counts and any broken references. Never present a fallback result as Precision output.

The standalone `scripts/flash_fallback.ps1` helper is available when a caller needs to run the fast fallback directly. For DOCX input it restores embedded images only when the Markdown image-reference count exactly matches the DOCX media count; it reports ambiguity instead of guessing.

If MinerU reports a size/page limit or unsupported type, explain the limit and suggest Precision mode with a valid token rather than silently downgrading.

The script prints the MinerU `task_id` or `batch_id`, result URL, image download counts, and output path. Include those details in the final response when useful.
