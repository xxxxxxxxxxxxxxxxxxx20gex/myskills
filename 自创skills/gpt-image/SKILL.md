---
name: gpt-image
description: "Generate, edit, or inpaint images with the OpenAI Images API. Use for text-to-image, reference-image editing, multi-reference composition, masked inpainting, posters, typography, Chinese text, UI mockups, diagrams, and gallery-based visual prompt design. Search the bundled reference gallery before calling scripts/generate.py."
---

# GPT Image

Use the bundled CLI for OpenAI-compatible Images API calls. Do not write a replacement SDK wrapper for normal image tasks.

## Configuration

Create a local `.env` in this skill directory from `.env_example`:

```dotenv
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key
```

- `OPENAI_BASE_URL` defaults to `https://api.openai.com/v1`. It may point to an OpenAI-compatible gateway; the CLI normalizes a missing `/v1` suffix.
- `OPENAI_API_KEY` is required. The process environment takes precedence over `.env`.
- Never print, commit, or modify a real key. Do not read global Codex configuration during normal use.

## Workflow

1. Classify the request as `generate`, `edit`, or `inpaint`; capture exact text, canvas, references, masks, and quality.
2. Read `references/gallery.md`, then load the closest one to three category files. Read `references/craft.md` for dense text, diagrams, UI, multi-panel layouts, or edits.
3. For an ambiguous, costly, or high-polish request, offer up to three directions and ask one concise question. For a precise “generate now” request, proceed.
4. Confirm output path and that every reference image and mask exists. A mask must be PNG and requires an input image.
5. Call `scripts/generate.py`, then report the produced path(s) and surface errors without secrets.

## CLI

```bash
python "$SKILL_DIR/scripts/generate.py" -p "PROMPT" [-f OUTPUT] [-i IMAGE ...] [-m MASK] [options]
```

Routing is automatic:

| Mode | Invocation | Official route |
|---|---|---|
| Text-to-image | no `-i` | `POST /v1/images/generations` JSON |
| Reference edit | one or more `-i` | `POST /v1/images/edits` multipart |
| Inpaint | `-i` and `-m` | `POST /v1/images/edits` multipart with PNG mask |

`-i` accepts local image paths. Repeating it sends multiple reference images to the edits endpoint. URLs are intentionally not accepted because the official edit API requires uploaded image files.

## Options

| Flag | Purpose |
|---|---|
| `-p`, `--prompt` | Required generation or edit instruction |
| `-f`, `--file` | Output path; an auto-named file is used when omitted |
| `-i`, `--image` | Repeatable local reference image |
| `-m`, `--mask` | PNG transparency mask for inpainting |
| `--model` | Defaults to `gpt-image-2`; override for a supported image model |
| `--size` | `1k`, `2k`, `4k`, `portrait`, `landscape`, `square`, `wide`, `tall`, or a literal size |
| `--quality` | `low`, `medium`, `high`, or `auto` |
| `-n` | Number of images |
| `--background` | `auto`, `opaque`, or `transparent` |
| `--moderation` | `auto` or `low` |
| `--input-fidelity` | `low` or `high`; applies to edits |
| `--format` | `png`, `jpeg`, or `webp` |
| `--compression` | JPEG/WebP compression from 0 to 100 |
| `--user` | Optional end-user identifier |

Use `medium` for exploration and `high` for final assets, dense Chinese typography, diagrams, UI, or paper figures. Use `portrait` for posters, `landscape` for photos and game scenes, `2k` for print-like figures, and `4k` for widescreen heroes.

## Reference Loading

- `references/gallery.md`: routing index for 162 collected prompts. Always load first.
- `references/gallery-*.md`: concrete category prompts. Load only the smallest useful slice.
- `references/craft.md`: prompt construction rules for exact text, diagrams, UI, edit invariants, and complex layouts.
- `references/openai-cookbook.md`: model/API examples; consult for API-semantics questions.

Preserve `Curated` and `Author + Source` attribution metadata when adapting gallery examples.
