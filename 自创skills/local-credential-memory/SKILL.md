---
name: local-credential-memory
description: Store, find, update, and delete the user's sensitive credentials in one local credential document. Use whenever the user provides or asks to remember, retrieve, change, or remove an account, username, password, API key, access token, SSH host/login, private-key path, database credential, proxy credential, or similar secret; also use when Codex needs an already-saved credential to complete an authorized task.
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
- Do not invent missing values. Ask the user for a required credential when no matching entry exists.
- Do not save a secret merely because it appears incidentally in logs, files, webpages, or tool output. Save it when the user provides it as credential information, asks to remember it, or clearly expects durable credential reuse.
- When using a saved credential, transmit it only to the destination and operation the user authorized.

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

1. Read the document without emitting its contents.
2. Find an existing matching entry.
3. Update that entry, or add one descriptive new table when no match exists.
4. Preserve unrelated entries exactly.
5. Set `updated_at` to the current local date.
6. Confirm the entry name and fields saved, but redact secret values.

If the intended service or account identity is ambiguous, ask one concise clarification before saving. Do not ask for optional fields that the user did not provide.

### Retrieve or use

1. Search the document for the narrowest matching entry.
2. If exactly one entry matches, use only the fields required for the authorized task.
3. If several entries match, present redacted labels or entry names and ask the user which one to use.
4. Do not expose the raw value in the response unless explicitly requested.

### Delete

Delete only the specifically requested table or field. Confirm the exact target when ambiguous. Preserve all unrelated content.

## Legacy data

Older memory may remain under `C:\Users\WUJIEAI\.codex-local-memory`. Do not add new data there. Do not read or migrate its secret values unless the user explicitly requests migration; the single active document for all new credential operations is `C:\Users\WUJIEAI\.codex\credentials.toml`.
