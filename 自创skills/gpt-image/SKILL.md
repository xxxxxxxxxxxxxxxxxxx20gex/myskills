---
name: gpt-image
description: "Use this skill whenever a user asks to generate, create, draw, render, or edit images with GPT Image 2 / gpt-image-2, text-to-image, reference-image editing, inpainting, posters, typography, Chinese text, UI mockups, diagrams, or gallery prompts. Analyze the user's prompt, search the bundled Reference Gallery/craft files for matching design patterns, confer on direction when useful, then call the bundled `scripts/generate.py`. Do not write new image-generation code unless explicitly asked to modify this repo."
compatibility: "Requires Python 3.11+ and RIGHT_CODES_API_KEY in the process environment or a local `.env` file. This local copy calls the Right Code relay at https://www.right.codes/draw directly; `gpt-image`, `uv`, and `uvx` are not required."
metadata: {"openclaw":{"requires":{"anyBins":["python"]},"primaryEnv":"RIGHT_CODES_API_KEY","homepage":"https://github.com/wuyoscar/gpt_image_2_skill"}}
---

# gpt-image

## Local Right Code Configuration

This workstation copy is intentionally configured to use the Right Code relay directly. `scripts/generate.py` loads `RIGHT_CODES_API_KEY` from the skill root `.env` file when present, while preserving any value already set in the process environment. It also injects `OPENAI_BASE_URL=https://www.right.codes/draw/v1` and `RIGHT_CODES_BASE_URL=https://www.right.codes/draw`, then calls the direct Right Code HTTP generation path. It does not require `gpt-image`, `uv`, or `uvx`.

Agent runbook for GPT Image 2 generation/editing. Use the prompt library + packaged CLI. Do not reimplement image API code.

## Operating loop

1. **Classify request**: `generate`, `edit`, `inpaint`, or `multi-reference`; identify asset type, exact text, aspect ratio, references, safety constraints, and budget/quality.
2. **Search references first**: open `references/gallery.md`; load/search the closest `references/gallery-<category>.md` file(s). Read actual `**Prompt**` text before choosing a pattern.
3. **Refine with craft**: load `references/craft.md` for dense text, diagrams, UI, data visualization, multi-panel layouts, weak prompts, or no close gallery match.
4. **Confer when useful**: before costly/ambiguous/high-polish calls, present 1–3 matched directions plus planned size/quality; ask at most one concise question. Skip long discussion for precise “generate now” requests.
5. **Preflight, no side effects**: use existing CLI/skill if present. Check command availability (`command -v gpt-image`), installed tool lists when the tool manager exists, or the runtime’s own skill registry when available. Do not assume a local home path in cloud/hosted runtimes.
6. **No blind setup**: do not reinstall, overwrite skill folders, create/modify `.env`, or write API keys unless the user explicitly requested setup. Global/shared installs are opt-in only.
7. **Execute via bundled script only**: call `scripts/generate.py`. Do not create a new `generate.py`, SDK wrapper, or ad-hoc script for normal image requests.
8. **Report**: output file path(s), key flags, and one concise refinement suggestion if useful.

Fast path: precise prompt + explicit “generate now” → quick reference/craft check, then CLI.

## CLI resolution

Preferred call:

```bash
python "$SKILL_DIR/scripts/generate.py" -p "PROMPT" [-f OUT] [-i REF...] [-m MASK] [options]
```

`scripts/generate.py` calls the local Right Code relay directly. Do not route through `gpt-image`, `uv`, or `uvx` for this workstation copy.

## Key and cost rules

- The script reads `RIGHT_CODES_API_KEY` from the process environment first, then from the skill root `.env` file. Do not commit real keys.
- If host/runtime has native platform-managed image generation and the user wants that path, use the host tool instead of this CLI.
- If `RIGHT_CODES_API_KEY` is unset, report the missing key or use host-native generation when requested; do not write secrets.
- Never print secret values.

## Flags

| Flag | Values | Use |
|---|---|---|
| `-p, --prompt` | string | Required prompt/edit instruction |
| `-f, --file` | path | Output path; auto-named if omitted |
| `-i, --image` | repeatable path | Use edits endpoint; supports multiple references |
| `-m, --mask` | PNG path | Inpaint with alpha mask; requires `-i` |
| `--model` | default `gpt-image-2` | Image model |
| `--size` | `1k`, `2k`, `4k`, `portrait`, `landscape`, `square`, `wide`, `tall`, or literal | Canvas size |
| `--quality` | `low`, `medium`, `high`, `auto` | Cost/quality dial |
| `-n, --n` | integer | Number of images |
| `--background` | `auto`, `opaque` | Generation background |
| `--moderation` | `auto`, `low` | Generation moderation setting |
| `--format` | `png`, `jpeg`, `webp` | Output encoding |
| `--compression` | `0-100` | JPEG/WebP compression |
| `--user` | string | Optional end-user identifier |

Quality policy:
- `low`: cheap drafts, broad exploration, many variants.
- `medium`: normal exploration, style probing, balanced cost.
- `high`: final assets, Chinese text, posters, diagrams, UI, paper figures, dense labels.

Size policy:
- default/social square: `1k` / `1024x1024`
- poster/mobile/beauty: `portrait`
- landscape/gameplay/photo: `landscape`
- print/paper figure: `2k`
- widescreen hero: `4k`
- vertical story/banner: `tall`

## Endpoint routing

| Mode | Trigger | Endpoint |
|---|---|---|
| Text-to-image | no `-i` | `/v1/images/generations` |
| Reference edit | one or more `-i` | `/v1/images/edits` |
| Inpaint | `-i` + `-m` | `/v1/images/edits` with mask |

Surface API errors verbatim enough for debugging; exit codes: `0` success, `1` API/refusal, `2` bad args/missing key.

## Reference loading

- `references/gallery.md`: routing index for the 162-prompt Reference Gallery Atlas. Load first.
- `references/gallery-*.md`: concrete prompts, previews, paths, metadata, attribution. Load 1 category for normal requests; 2–3 for hybrids.
- `references/craft.md`: prompt-craft checklist. Load for prompt repair, exact text, UI/data/diagram grammar, edit invariants, and multi-panel consistency.
- `references/openai-cookbook.md`: official parameter/model semantics. Load for API behavior or model capability questions.

Reference loading policy: load the smallest useful slice; never load all category files by default.

## Verification

- Before API call: confirm endpoint mode, size, quality, output path, and required reference/mask files.
- After CLI call: report path(s) printed by the CLI and surface stderr on failure.
- For edits/inpaints: verify `-i` paths exist; verify `-m` exists when used.

Preserve `Curated` vs `Author + Source` metadata when adapting examples. Add new collected prompts to the Reference Gallery before README promotion.
