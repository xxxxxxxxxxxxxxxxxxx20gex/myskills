---
name: local-credential-memory
description: Store, discover, import, find, update, and delete the user's sensitive credentials in one local credential document. Use whenever the user provides or asks to remember, retrieve, change, remove, or reuse an account, username, password, API key, access token, SSH host/login, private-key path, database credential, proxy credential, or similar secret; when the user authorizes Codex to inspect local configuration for credentials; and when Codex needs a saved or locally discoverable credential to complete an authorized task.
---

# Local Credential Memory

Maintain exactly one credential document:

```text
C:\Users\WUJIEAI\.codex\credentials.toml
```

Use this skill only for credentials and secrets. Do not store general preferences, project notes, troubleshooting, plans, or ordinary machine facts.

## Security rules

- Treat the document as plaintext sensitive data even though access is restricted to the current Windows user.
- Never print, summarize, log, or quote the whole document.
- Read only the entry needed for the current authorized task.
- In normal responses, identify a credential by entry name and redact secret values. Reveal a raw secret only when the user explicitly asks to see that specific value.
- Never place a secret in source code, Git, project documentation, terminal history, screenshots, or unrelated files.
- Do not invent missing values. When no matching entry exists, first complete any locally authorized discovery workflow; ask the user only after the allowed sources have been exhausted.
- Do not save a secret merely because it appears incidentally in logs, files, webpages, or tool output. Save it when the user provides it as credential information, asks to remember it, or clearly expects durable credential reuse.
- When using a saved credential, transmit it only to the destination and operation the user authorized.

## Authorized discovery and import

A missing credential entry or an empty/missing `credentials.toml` is a discovery trigger, not a stopping condition.

Treat instructions such as the following as explicit authorization to inspect the named local configuration, import the matching credential, and reuse it for the authorized task:

- “去我的 Codex 配置里找。”
- “密钥和路由在本机配置里。”
- “你可以从这个配置文件知道 key 和 URL。”
- “找到后下次直接用。”

For Codex provider credentials, inspect only the narrow sources needed, normally:

1. `C:\Users\WUJIEAI\.codex\config.toml` for the active provider, `base_url`, protocol, and referenced environment variable names.
2. The current process environment for an explicitly referenced variable such as `OPENAI_API_KEY`.
3. `C:\Users\WUJIEAI\.codex\auth.json` when the provider uses Codex/OpenAI authentication and the required value is not already resolved from the active source.

Do not print raw values while discovering them. Report only source presence, redacted identity, or a short fingerprint when comparison is necessary.

When discovery yields one complete and unambiguous credential:

1. Create `credentials.toml` if it does not exist.
2. Save or update a stable entry immediately.
3. Include relevant routing fields such as `base_url`, provider name, username, host, or port.
4. Record a non-secret `notes` description of the authorized source and set `updated_at`.
5. Use the newly imported credential for the current authorized task; do not require a second user request.

If several candidate secrets differ, prefer the source the user explicitly identified as active. If the user did not identify one, present only redacted source labels and ask which candidate to import. Never merge or save multiple conflicting candidates silently.

## Document format

Store each credential under a stable, descriptive TOML table. Prefer names such as `github.personal`, `ssh.production_server`, `database.analytics`, or `api.openai`.

Use only relevant fields:

```toml
[ssh.example_server]
kind = "ssh"
label = "Example production server"
host = "example.com"
port = 22
username = "deploy"
password = "..."
private_key_path = "C:\\Users\\WUJIEAI\\.ssh\\id_ed25519"
notes = "Use key authentication when available"
updated_at = "YYYY-MM-DD"

[api.example]
kind = "api_key"
label = "Example API"
api_key = "..."
base_url = "https://api.example.com"
updated_at = "YYYY-MM-DD"
```

Escape TOML strings correctly. Do not duplicate a credential because its wording differs; search existing table names, labels, hosts, usernames, and service names first.

## Workflow

### Record or update

1. Resolve values supplied by the user or found through an explicitly authorized local discovery workflow.
2. Read the credential document without emitting its contents; create it when missing.
3. Find an existing matching entry by table name, label, host, account, provider, or `base_url`.
4. Update that entry, or add one descriptive new table when no match exists.
5. Preserve unrelated entries exactly.
6. Set `updated_at` to the current local date.
7. Confirm the entry name, non-secret routing fields, and secret fields saved, but redact secret values.

If the intended service or account identity is ambiguous, ask one concise clarification before saving. Do not ask for optional fields that the user did not provide.

### Retrieve or use

1. Search the document for the narrowest matching entry.
2. If exactly one entry matches, use only the fields required for the authorized task.
3. If several entries match, present redacted labels or entry names and ask the user which one to use.
4. If no entry matches and the user authorized a local configuration source, discover and import the credential, then continue the current task.
5. Ask the user for a missing value only after saved entries and authorized local sources have both been exhausted.
6. Do not expose the raw value in the response unless explicitly requested.

### Delete

Delete only the specifically requested table or field. Confirm the exact target when ambiguous. Preserve all unrelated content.

## Legacy data

Older memory may remain under `C:\Users\WUJIEAI\.codex-local-memory`. Do not add new data there. Do not read or migrate its secret values unless the user explicitly requests migration; the single active document for all new credential operations is `C:\Users\WUJIEAI\.codex\credentials.toml`.
