---
name: mineru-to-markdown
description: Convert local files or public URLs to Markdown with the MinerU cloud API, with optional OCR, tables, formulas, images, and page ranges. Use when Codex needs to parse, OCR, or extract Markdown from PDF, DOC/DOCX, PPT/PPTX, image, Excel, or HTML documents, whether or not the user already has a MinerU API token.
---

# MinerU To Markdown

Use `scripts/convert.py` for MinerU API conversion instead of rewriting HTTP polling code.

## Quick Start

Resolve this skill's directory from the loaded `SKILL.md`, then run `<skill-directory>/scripts/convert.py`. Do not assume the skill is installed at a fixed path.

By default, the script reads `MINERU_API_TOKEN` from `<skill-directory>/.env` first. If a token exists, it uses Precision mode; otherwise, it uses Agent Lightweight mode.

Default output creates one exportable folder per source file when `--out` is omitted:

```text
<skill-directory>/workspace/<source-name>/<source-name>.md
<skill-directory>/workspace/<source-name>/images/
```

```powershell
python "<skill-directory>\scripts\convert.py" "C:\path\paper.pdf"
python "<skill-directory>\scripts\convert.py" "https://example.com/paper.pdf"
```

If the user has a token, create `<skill-directory>/.env` from `.env.example` to enable token-backed Precision mode. Never ask the user to paste a token into chat or include it in the final response:

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

When no token is configured, try Agent Lightweight mode directly. If MinerU rejects the file because of its size, format, access URL, or service limit, explain the reported limitation and ask the user to configure `MINERU_API_TOKEN` locally for Precision mode. Do not claim that a token is required before the token-free attempt fails.

If the script reports `images_unavailable`, explain that Agent Lightweight returned only `<!-- image-->` placeholders and no downloadable image URLs. Use Precision mode for reliable image extraction. Do not automatically pair embedded PDF image objects with placeholders because one rendered figure may contain multiple raster, vector, and text objects.

## Verification

After conversion, open or inspect the generated Markdown. If `FLASH_FALLBACK_USED=true` appears, the final response MUST explicitly state that a degraded flash/Agent fallback was used, why Precision mode failed, and that table, formula, OCR, and complex-layout fidelity may be lower. Report image/asset counts and any broken references. Never present a fallback result as Precision output.

The standalone `scripts/flash_fallback.ps1` helper is available when a caller needs to run the fast fallback directly. For DOCX input it restores embedded images only when the Markdown image-reference count exactly matches the DOCX media count; it reports ambiguity instead of guessing.

If MinerU reports a size/page limit or unsupported type, explain the limit and suggest Precision mode with a valid token rather than silently downgrading.

The script prints the MinerU `task_id` or `batch_id`, result URL, image download counts, and output path. Include those details in the final response when useful.
