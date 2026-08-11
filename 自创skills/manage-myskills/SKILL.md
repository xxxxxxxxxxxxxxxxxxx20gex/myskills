---
name: manage-myskills
description: Manage the local myskills repository through conversation. Use when the user wants to search for Skills locally or online; inspect, import, create, copy, install, edit, rename, categorize, validate, test, delete, restore, or compare Skills; update the Skill catalog or project modules; diagnose repository state; restart the Playground; or synchronize changes with Git by committing and pushing. This Skill owns repository maintenance workflows, not the behavior of the managed Skills themselves.
---

# Manage MySkills

Manage the repository directly with Codex filesystem, browser, testing, and Git tools. Treat the web page as a catalog and execution surface, not as a file manager.

## Resolve the repository

1. Prefer an explicit path from the user.
2. Otherwise use the current Git worktree when it contains `AGENTS.md`, `自创skills/`, `已测skills/`, and `待测skills/`.
3. Otherwise try `~/Desktop/myskills`.
4. Stop if more than one plausible repository remains.

Read the repository `AGENTS.md` completely before changing anything. Inspect `git status --short` first and preserve unrelated or user-generated changes.

## Route the request

- For listing, searching, comparing, or explaining, perform read-only inspection and return evidence-backed results.
- For importing or creating, inspect the source before copying and choose the destination from the classification rules below.
- For edits, touch the smallest coherent set of files and keep the Skill’s own instructions authoritative.
- For deletion, move the Skill into `.skill-trash/` with a timestamp; do not permanently erase it unless the user explicitly asks for permanent deletion.
- For broad requests such as “同步项目” or “更新页面”, audit all required catalog, status, validation, restart, and Git steps.

## Search and inspect Skills

Search in this order:

1. The three repository Skill directories.
2. Installed Codex Skills under `${CODEX_HOME}/skills` or `~/.codex/skills` when relevant.
3. User-provided local paths, archives, or repository URLs.
4. Remote sources when the user asks to find or import a Skill.

Use `rg --files` and targeted `rg` searches first. Read `SKILL.md`, `agents/openai.yaml`, directly referenced resources, dependencies, scripts, license information, and suspicious executable behavior. Never print or copy secrets found during inspection.

When presenting search results, include location, maintenance class, purpose, dependencies, validation status, and a concise security observation. Do not claim a Skill is tested merely because its structure is valid.

## Import safely

Accept a local directory, ZIP, installed Skill, or Git repository as a source.

1. Stage external downloads in a temporary directory outside the repository.
2. Require one Skill root containing `SKILL.md`; reject ambiguous multi-Skill packages unless the user selects entries.
3. Reject path traversal, hidden credential stores, `.env`, private keys, tokens, caches, build output, `.git`, and unrelated repository files.
4. Review executable scripts before running them. Structural validation never authorizes unknown code execution.
5. Refuse to overwrite an existing Skill silently. Compare or ask before merging materially different content.
6. Copy only files required by the Skill.
7. Validate the imported Skill and update repository metadata in the same change.

Classify the destination:

- `自创skills/`: created here or substantially customized for this repository.
- `已测skills/`: externally sourced and actually exercised successfully in its key workflow.
- `待测skills/`: externally sourced but not yet functionally verified. This is the default for imports.

## Create and edit

For a new Skill, follow the installed `skill-creator` workflow: initialize with its script, write concise trigger metadata and imperative instructions, generate `agents/openai.yaml`, and run `quick_validate.py`.

For an update:

- Preserve the Skill’s scope unless the user asks to change it.
- Keep `SKILL.md` under 500 lines when practical and move detailed material into one-level references.
- Prefer bundled scripts for repeated deterministic operations and test changed scripts directly.
- Never add README, changelog, credentials, or unrelated project notes inside a Skill.

## Rename, move, delete, and restore

When a Skill path changes, migrate matching keys in `skill-metadata.yaml` and `skill-insights.yaml`. Update its functional category mapping and any curated display entry. Ensure only one active copy remains across the three maintenance directories.

For deletion, move the directory to `.skill-trash/<timestamp>-<class>-<name>/`, remove stale catalog references and metadata keys, then validate the remaining catalog. For restoration, reverse the move only when the destination name is free.

## Synchronize the project

After every repository mutation:

1. Re-scan actual Skill directories and update `playground/static/js/data.js` only where curated display data or functional category assignment is required.
2. Update `AGENTS.md` when module structure or maintenance behavior changes.
3. Run `python playground/generate_project_status.py`; do not hand-edit generated tables.
4. Validate every added or modified Skill with the repository validator or the `skill-creator` validator.
5. Run all relevant Python and JavaScript regression tests plus `git diff --check`.
6. Handle the Playground runtime safely:
   - When `MYSKILLS_PLAYGROUND_RUN=1`, the current task is hosted by the Playground. Never stop, kill, restart, or replace the process serving `MYSKILLS_PLAYGROUND_URL`; doing so would terminate the active task. Request `/api/skills` after Skill directory changes to refresh project registration, then verify the existing `/`, `/api/config`, and `/api/skills` endpoints. Static page changes take effect after a browser reload. If backend or startup changes truly require a process restart, report `restart required` and defer it until after the current web task has returned.
   - Outside a Playground-hosted task, restart the Playground normally, keep it bound to `127.0.0.1`, and verify `/`, `/api/config`, and `/api/skills`.
7. Inspect the explicit staged file list and scan it for secrets. Never use `git add -A` and never stage `.env`, `.runs/`, `.skill-trash/`, credentials, or unrelated user changes.
8. Commit the completed mutation and push the current branch immediately through Git Credential Manager. Use the project proxy configuration when needed. If push fails, preserve the local commit and report its ID.

Do not commit merely read-only investigation. Do not modify or install a second copy under `~/.codex/skills` unless the user specifically requests installation there.

## Completion report

Lead with the outcome. State the affected Skill paths, classification, validation and regression results, whether restart was completed or safely deferred, commit ID, push result, and any intentionally preserved local changes. Redact every credential.
