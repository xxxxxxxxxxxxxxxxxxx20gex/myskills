---
name: local-operator-memory
description: Record and reuse local operational knowledge for this machine. Use when a task reveals reusable local experience from Codex/agent actions, including project creation or clone, Git/GitHub/Gitee repository setup, branch/status discoveries, AGENTS.md maintenance, Multica/Codex configuration, user/HOME/path decisions, VS Code remote user behavior, network/proxy fixes, service/daemon/port issues, environment setup, command failures that were fixed, user preferences, or requests to remember, recall, index projects, store credentials, or reuse prior local troubleshooting knowledge.
---

# Local Operator Memory

## Purpose

Use this skill to preserve useful local working knowledge discovered while operating on this machine. Record facts that reduce repeated probing: verified paths, project locations, Git state, setup/run/test procedures, failures and fixes, network/proxy workarounds, Multica/Codex behavior, user preferences, and explicit secrets.

This skill is not a policy constraint. It is a local operational memory layer that helps future agents act with less repeated discovery.

## Storage

Default memory root:

```bash
${CODEX_LOCAL_MEMORY_DIR:-$HOME/.codex-local-memory}
```

Primary files:

```text
INDEX.md
machine.md
users.md
network.md
multica-codex.md
projects.md
troubleshooting.md
preferences.md
lessons.jsonl
projects.json
.env
```

Use `.env` only for explicit secrets or sensitive values the user asks to preserve. Keep `.env` mode `600`. Do not print `.env` contents in responses or command output summaries.

## Workflow

Before acting, read relevant memory when the task touches local setup, projects, Multica, Codex, users, shells, VS Code remote, network, proxies, services, ports, or known repositories:

```bash
python3 "$HOME/.codex/skills/local-operator-memory/scripts/memory.py" search --query "<task keywords>"
```

Windows PowerShell:

```powershell
python "$env:USERPROFILE\.codex\skills\local-operator-memory\scripts\memory.py" search --query "<task keywords>"
```

After acting, decide whether the task revealed reusable local knowledge. Record only durable, useful facts:

```bash
python3 "$HOME/.codex/skills/local-operator-memory/scripts/memory.py" add \
  --category troubleshooting \
  --title "Short reusable lesson" \
  --scope machine \
  --content "What happened, what worked, when to reuse it." \
  --evidence "Command/config/path observed." \
  --confidence verified
```

For explicit secrets:

```bash
python3 "$HOME/.codex/skills/local-operator-memory/scripts/memory.py" secret set NAME "value"
python3 "$HOME/.codex/skills/local-operator-memory/scripts/memory.py" secret get NAME
python3 "$HOME/.codex/skills/local-operator-memory/scripts/memory.py" secret unset NAME
```

Windows PowerShell:

```powershell
python "$env:USERPROFILE\.codex\skills\local-operator-memory\scripts\memory.py" secret set NAME "value"
python "$env:USERPROFILE\.codex\skills\local-operator-memory\scripts\memory.py" secret get NAME
python "$env:USERPROFILE\.codex\skills\local-operator-memory\scripts\memory.py" secret unset NAME
```

Only store raw secrets when the user explicitly asks to save that exact sensitive value. For ordinary logs and lessons, redact secrets and refer to `.env` keys by name. The helper script quotes `.env` values for shell-style storage and redacts common token/password/proxy patterns from normal search output, but do not intentionally place raw secrets in Markdown or JSON.

## Project Context

When creating, cloning, indexing, or modifying a project, update project memory and project `AGENTS.md`:

```bash
python3 "$HOME/.codex/skills/local-operator-memory/scripts/project_context.py" update --project /path/to/project
```

Windows PowerShell:

```powershell
python "$env:USERPROFILE\.codex\skills\local-operator-memory\scripts\project_context.py" update --project "C:\path\to\project"
```

The script updates:

```text
<project>/AGENTS.md
$CODEX_LOCAL_MEMORY_DIR/projects.md
$CODEX_LOCAL_MEMORY_DIR/projects.json
```

It only replaces content between these markers in `AGENTS.md`:

```markdown
<!-- local-operator-memory:start -->
<!-- local-operator-memory:end -->
```

Preserve human-written AGENTS.md content outside the managed block.

## What To Record

Record when at least one condition is true:

- A command failed, then a working fix was found.
- A path, config file, daemon, token location, or user-specific HOME behavior was verified.
- A project was created, cloned, moved, initialized, or meaningfully changed.
- A Git branch, remote, commit, or repository role became important for future work.
- A setup, run, test, build, deploy, or login procedure was verified.
- A proxy, mirror, registry, package source, or network workaround solved a real issue.
- A user preference changed how future work should be performed.
- The user explicitly asked to remember or reuse something.

Do not record routine command output, temporary failed attempts with no future value, or large logs. Summarize the reusable lesson.

## Record Format

Each lesson should include:

```text
Scope: global | machine | user | project | repo
Applies to: path/user/tool/project when relevant
Symptom: what failed or was uncertain
Working fix: what worked
Reuse rule: when to apply or verify this next time
Evidence: command result, file path, or user confirmation
Confidence: verified | user-confirmed | inferred
Last confirmed: local date
```

## Security Handling

Use this split:

- Markdown/JSON: facts, paths, lessons, redacted references.
- `.env`: explicit sensitive values such as passwords, tokens, private proxy URLs, API keys.

Rules:

- Never echo raw `.env` values in final answers.
- Prefer key names such as `MULTICA_TOKEN` or `COMPANY_PROXY_URL` in Markdown.
- Keep `.env` permissions at `600`.
- If a captured command output contains an accidental secret, do not write it to Markdown.

## Local References

Read `references/memory-schema.md` when changing the memory format or adding new categories.
