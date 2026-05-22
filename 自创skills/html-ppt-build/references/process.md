# HTML PPT Production Playbook

## Why HTML Instead of Direct Image Slides

Direct image slides are weak for Chinese technical decks: text becomes blurry or wrong, layout is hard to control, styles drift between pages, and small edits require redrawing the whole slide.

HTML solves this by separating concerns:

- HTML/CSS: text, hierarchy, layout, tables, cards, diagrams, page-specific control.
- Generated images: visual atmosphere, backgrounds, architecture concepts, non-text diagrams.
- Chrome screenshots: final visual fidelity.

## Recommended Sequence

1. Convert source files to Markdown.
2. Extract project story, scoring criteria, modules, metrics, and constraints.
3. Write `PPT制作大纲.md` with page number, theme, content, and visual form.
4. Build initial `deck.css` and 1-2 representative pages.
5. Generate pages in batches of 2-3.
6. Add `slide-XX.css` for any page with unique geometry.
7. Make `all-slides.html` as the review surface.
8. Iterate the weakest pages with layout-first changes.
9. Use generated images for visual breaks and complex conceptual visuals.
10. Export to high-resolution image PPTX.

## Batch Size

Prefer 2-3 pages per generation pass. More pages in one pass tends to reduce page-specific thinking and increases context load. If the deck is longer than 20 pages, keep the outline and file structure as the source of truth rather than trying to keep all page code in context.

## File Boundaries

Keep each slide self-contained:

- `slide-08.html` should be editable without reading all other slides.
- `slide-08.css` may import `deck.css`, but should not require another slide's CSS.
- Global rules should be stable and boring.

## Review Rhythm

Review at three scales:

- Single page: text fit, hierarchy, logic, visual form.
- Contact sheet/index: rhythm, repetition, density, section changes.
- Exported PPTX: screenshot sharpness, page count, aspect ratio, media size.

## Common Fixes

- Too many cards: convert to process, matrix, timeline, or generated concept figure plus labels.
- Dense Chinese text: split into labeled microcopy and use a conclusion strip.
- Generic title: rewrite as a claim.
- Weak image: keep image as background only and overlay real labels in HTML.
- Export has borders: inject export CSS to remove body padding and shadows.
- Export is blurry: raise device scale factor to 2 or 3.
