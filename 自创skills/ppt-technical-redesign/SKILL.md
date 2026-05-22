---
name: ppt-technical-redesign
description: Redesign plain PPT or slide content into professional, high-density technical presentation pages. Use when Codex needs to restructure or rewrite PowerPoint/PPTX slides, project proposal pages, defense decks, technical route pages, architecture diagrams, product capability pages, research reports, or competition presentations to make them more logical, visually technical, information-rich, and project-specific.
---

# PPT Technical Redesign

Use this skill to transform plain slide content into a professional technical presentation page. Prioritize clearer project communication over decoration.

## Workflow

1. Identify the slide's job: problem framing, system architecture, technical route, module explanation, experiment result, product value, comparison, timeline, or conclusion.
2. Extract the core message into one headline sentence. The page should answer one question, not list unrelated facts.
3. Replace bullet piles with a structured visual form: module map, layered architecture, process flow, comparison matrix, metric dashboard, capability grid, timeline, risk-control loop, or before/after contrast.
4. Increase useful information density by adding labels, microcopy, indicators, constraints, metrics, inputs/outputs, arrows, callouts, and evidence points.
5. Apply a restrained technical aesthetic: blue-white or dark technical palette, thin lines, numbered badges, iconized nodes, circuit/grid accents, compact typography, and clear visual hierarchy.
6. Preserve factual meaning. Do not invent performance numbers, architecture modules, or claims unless the user asks for proposed copy; mark inferred items as placeholders.
7. For PPTX edits, use the presentations skill/plugin workflow if available, render screenshots, and iterate until text does not overflow and the page reads clearly.

## Layout Selection

- Architecture or system composition: use a layered architecture, hub-and-spoke module map, or left-to-right data pipeline.
- Algorithm or processing logic: use numbered process flow with input, method, output, and feedback loop.
- Product features: use capability cards grouped by user workflow or technical subsystem.
- Research/project advantages: use problem-solution-proof structure with metrics and evidence callouts.
- Comparison content: use matrix/table with highlight bands and decision markers.
- Roadmap or implementation plan: use timeline, phase lanes, milestones, and deliverable tags.
- Dense explanatory page: use a two-column layout with visual model on one side and structured detail panels on the other.

Load references only as needed:

- Load `references/layout-patterns.md` when choosing a concrete visual pattern or writing a redesign spec.
- Load `references/decision-table.md` when the source content is ambiguous and you need to choose between pipeline, matrix, architecture, dashboard, timeline, or audit-loop layouts.
- Load `references/style-systems.md` when the user asks for visual style, deck-wide consistency, or a stronger design direction.
- Load `references/chinese-copywriting.md` when rewriting Chinese titles, subtitles, module names, bullets, or report-style copy.
- Load `references/domain-playbooks.md` when the slide belongs to healthcare AI, research defense, enterprise software, industrial systems, government projects, or data governance.
- Load `references/anti-patterns.md` when reviewing an existing slide, explaining why it feels weak, or deciding what to remove.
- Load `references/ppt-implementation.md` when editing PPTX directly or giving concrete layout, typography, spacing, and verification parameters.
- Load `references/review-checklist.md` before finalizing a slide rewrite or PPTX edit.

## Technical Visual Style

Prefer project-book / defense-PPT technical visuals:

- Use clear title hierarchy: page title, one-line takeaway, section labels, node labels, and small explanatory captions.
- Use diagrams as the main content, not decorative side art.
- Use compact but readable text blocks; split long paragraphs into labeled evidence points.
- Use arrows only when they encode real data/control flow.
- Use icons for technical entities: sensor, chip, API, model, database, queue, graph, dashboard, cloud, edge device, user, warning, shield.
- Use accent color sparingly for key outputs, risks, or winning evidence.
- Keep repeated shapes aligned to a grid. Avoid random floating cards.

## Output Expectations

When asked to improve a page, provide or implement:

- The slide job and one-sentence core message.
- A refined headline and takeaway.
- A proposed page structure.
- Rewritten slide copy grouped by visual blocks.
- Specific diagram/layout instructions that can be implemented in PPT.
- If editing PPTX directly, an updated deck plus a concise note about changed slides and verification.

For Chinese project or competition decks, write polished Chinese copy unless the source deck is English.
