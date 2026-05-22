---
name: html-ppt-build
description: Use when building high-density Chinese technical PPTs as HTML slides, especially from Markdown/report materials into independent slide-XX.html/CSS pages, visual assets, all-slides preview indexes, and high-resolution image-based PPTX exports. Use for project proposal decks, defense decks, architecture decks, and AI-assisted PPT production workflows where direct image generation is too blurry or hard to edit.
---

# HTML PPT Build

Build PPT decks as fixed-canvas HTML pages, then export to high-resolution image-based PPTX only at the end. Prefer this workflow when Chinese text clarity, dense technical layout, rapid iteration, and page-level control matter more than native PowerPoint editability.

## Core Rule

Do not ask an image model to draw complete text-heavy slides. Use HTML/CSS for Chinese text, layout, tables, cards, arrows, and page structure. Use generated images only as visual assets: backgrounds, architecture illustrations, relationship diagrams, flow visuals, product scenes, or non-text concept figures.

## Workflow

1. Convert source materials to Markdown first when source files are PDF/DOCX/PPTX/images. Use `mineru-to-markdown` if available and appropriate.
2. Create a slide outline before writing pages. Each row should include page number, page theme, core content, and visual form.
3. Generate pages in small batches, normally 2-3 slides per pass. Avoid generating an entire 20-40 page deck in one context.
4. Use one independent `slide-XX.html` per page. Keep each page readable and editable on its own.
5. Use a shared `deck.css` for design-system basics. Give complex pages their own `slide-XX.css` that imports `deck.css`.
6. Use `ppt-technical-polish` for single-slide layout decisions: pipeline, matrix, architecture, timeline, capability grid, audit loop, etc.
7. Use `gpt-image` for pages that are visually repetitive or too card/table-heavy, but keep final Chinese text overlaid in HTML.
8. Create or maintain `all-slides.html` as a browsing index for fast review and page-level navigation.
9. Preview and fix individual pages before exporting the PPTX.
10. Export via high-resolution Chrome screenshots and insert each PNG full-slide into a 16:9 PPTX.

## Recommended Project Layout

```text
project/
  PPT制作大纲.md
  all-slides.html
  deck.css
  slide-01.html
  slide-02.html
  slide-03.html
  slide-04.html
  slide-04.css
  ...
  assets/
  images/
  _preview/
  _export_hd_png/
```

`deck.css` should hold only shared foundations: fonts, colors, `.slide` size, title block, common cards, common grids, and common backgrounds.

`slide-XX.css` should hold page-specific structure. Do not put one page's special geometry into `deck.css` if that change could affect unrelated slides.

## Fixed Canvas Rules

Use a PPT-like fixed canvas:

```css
.slide {
  width: 1600px;
  height: 900px;
  overflow: hidden;
}
```

Avoid relying on live viewport behavior for final layout. Browser preview may scale the slide for convenience, but export must force 1600x900 and no body padding.

## Page Design Rules

Each slide should have one job and one memorable claim. The usual structure is:

```text
top: kicker + title + subtitle + page number
middle: one main proof object or diagram
bottom: takeaway, value strip, or conclusion sentence
```

Choose visual forms by content:

- Background/policy: trend chain, timeline, goal-system-measure, governance matrix.
- Pain point: funnel, before/after, risk chain, source-to-failure map.
- Architecture: layered architecture, hub-and-spoke, data pipeline.
- Algorithm/process: numbered flow with input/method/output and checkpoints.
- Product capabilities: capability grid grouped by workflow or subsystem.
- Innovation/comparison: comparison matrix, four-quadrant matrix, proof strip.
- Safety/governance: evidence chain, audit trail, review gate, control loop.

## Generated Image Rules

Use generated images to reduce visual fatigue and improve slide rhythm, especially after several dense HTML-only pages.

Good generated assets:

- cover hero image
- section background
- platform or workflow scene
- architecture concept visual
- knowledge graph/evidence chain visual
- non-text flow or relationship illustration

Avoid generated images for:

- exact Chinese copy
- dense tables
- editable labels
- precise metrics
- slide pages likely to need frequent text edits

Prompt generated images with constraints such as:

```text
no readable text anywhere
avoid fake Chinese characters
leave clean area for overlaid slide text
dark technical presentation background
```

## Export

Use `scripts/export_html_pptx_hd.py` when the project is a folder of `slide-*.html` files. It creates 3200x1800 PNGs by default and inserts them into a 16:9 PPTX without cropping.

Typical Windows command:

```powershell
python C:\Users\23262\.codex\skills\html-ppt-build\scripts\export_html_pptx_hd.py `
  --project "D:\path\to\deck-folder" `
  --output "D:\path\to\deck-folder\deck-name-高清图片版.pptx"
```

The script injects temporary export CSS into a copied project, so source HTML/CSS preview behavior is not modified.

## Validation Checklist

Before final delivery:

- `all-slides.html` exists or another full-deck preview exists.
- Every `slide-XX.html` renders independently.
- Complex pages have page-specific CSS instead of leaking rules into unrelated pages.
- Generated images do not contain important Chinese text.
- Export PNGs are 3200x1800 or higher.
- PPTX page size is 16:9.
- PPTX has one full-slide image per slide.
- Spot-check early, middle, complex, and final slides.

## References

- Read `references/process.md` for the detailed production playbook.
- Read `references/page-patterns.md` for slide-type layout selection.
