# Anti-Patterns

Use this file when reviewing an existing slide or deciding what to remove.

## Floating Card Soup

Symptoms:
- Many cards float independently.
- There is no primary diagram or reading order.
- Cards have similar visual weight even when their importance differs.

Fix:
- Choose one main structure: pipeline, architecture, matrix, timeline, or loop.
- Use cards as nodes inside that structure, not as decoration.

## Decorative Tech

Symptoms:
- Heavy grids, glowing lines, or circuit patterns.
- The actual content remains a bullet list.
- Visual effects compete with labels.

Fix:
- Every line should represent data flow, control flow, hierarchy, or relationship.
- Remove decoration that does not explain the content.

## Fake Dashboard

Symptoms:
- Random KPIs or charts without source data.
- Dashboard panels exist only for visual density.

Fix:
- Use real metrics if provided.
- If no metrics exist, use a workflow, capability map, or evidence structure instead.
- Mark inferred values as placeholders when the user asks for proposed copy.

## Overloaded Title

Symptoms:
- Title exceeds two lines.
- Title includes multiple unrelated claims.
- The page does not answer one clear question.

Fix:
- Keep one core claim in the title.
- Move context to subtitle and details to modules.

## Paragraph Slide

Symptoms:
- Long paragraphs occupy the body.
- The slide depends on narration to be understood.

Fix:
- Convert paragraphs into labeled nodes, comparison rows, steps, or callouts.
- Keep only one short takeaway sentence.

## Icon Wallpaper

Symptoms:
- Many icons appear without functional grouping.
- Icons are used to make the page look technical rather than explain meaning.

Fix:
- Use icons only for stable entities such as data source, model, database, API, user, cloud, device, shield, graph, or dashboard.
- Pair every icon with a precise label.

## One-Note Palette

Symptoms:
- The page is dominated by one hue family.
- Accent color is used everywhere, so nothing is emphasized.

Fix:
- Limit accent color to current stage, output, risk, or conclusion.
- Add neutral contrast through white, gray, dark, or muted secondary colors.
