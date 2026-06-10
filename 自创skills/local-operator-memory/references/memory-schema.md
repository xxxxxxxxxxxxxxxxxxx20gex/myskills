# Local Operator Memory Schema

## Categories

- `machine`: host-level facts, OS behavior, installed tools, ports, services.
- `users`: user accounts, HOME directories, VS Code remote user behavior, permission notes.
- `network`: proxies, mirrors, package registries, connectivity workarounds.
- `multica-codex`: Multica and Codex paths, daemon behavior, config locations.
- `projects`: project registry, repository summaries, setup/run/test notes.
- `troubleshooting`: failures, fixes, reusable diagnostics.
- `preferences`: user preferences that affect future execution.

## Lesson JSONL Entry

```json
{
  "created_at": "2026-05-23T12:00:00+08:00",
  "last_confirmed": "2026-05-23",
  "category": "troubleshooting",
  "title": "GitHub release download needs proxy",
  "scope": "machine",
  "content": "Short reusable lesson.",
  "evidence": "Observed command/fix.",
  "confidence": "verified",
  "tags": ["network", "github"]
}
```

## Project JSON Entry

```json
{
  "path": "/home/example",
  "name": "example",
  "is_git": true,
  "remote": "git@github.com:org/example.git",
  "branch": "main",
  "commit": "abc1234",
  "status": "clean",
  "last_seen": "2026-05-23T12:00:00+08:00",
  "summary": "Short project purpose or observed role."
}
```

## Secret `.env`

Secrets use shell-style `KEY=value` lines. Values are not automatically exported.

Recommended names:

```dotenv
COMPANY_PROXY_URL=
MULTICA_TOKEN=
GITHUB_TOKEN=
GITEE_TOKEN=
```

Do not duplicate raw secret values into Markdown or JSON.
