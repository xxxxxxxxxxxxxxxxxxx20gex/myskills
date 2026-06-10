---
name: temporary-public-file-links
description: Upload local files or directories to short-lived public URLs so a user can view artifacts that are not visible through Multica attachments, such as screenshots, reports, archives, logs, or generated media. Use when the user asks to share local files through temporary public links, expose screenshots for inspection, or work around failed/invisible platform attachments.
---

# Temporary Public File Links

Use this skill when local artifacts need a browser-viewable public URL and platform attachments are unavailable, invisible, or failing.

## Workflow

1. Confirm the requested paths exist and do not contain secrets, private keys, tokens, credentials, customer data, or sensitive source code.
2. For screenshots and other small artifacts, upload individual files. For directories or many files, let the script create a temporary zip archive.
3. Run:

```bash
python3 .codex/skills/temporary-public-file-links/scripts/upload_temp.py <path> [<path> ...]
```

4. Share only the resulting URLs, expiry notes, and any files that failed.
5. Do not use this for confidential material unless the user explicitly accepts that the files will be publicly accessible to anyone with the link.

## Script Behavior

- Files are uploaded as-is.
- Directories are zipped before upload.
- Multiple public hosting providers are tried until one succeeds.
- The script prints JSON with `uploads`, `failures`, provider names, and local source paths.
- Links are temporary and provider-dependent; assume they may expire or be deleted without notice.

## Useful Options

```bash
python3 .codex/skills/temporary-public-file-links/scripts/upload_temp.py --provider temp.sh ./screenshots
python3 .codex/skills/temporary-public-file-links/scripts/upload_temp.py --provider file.io image.png
python3 .codex/skills/temporary-public-file-links/scripts/upload_temp.py --max-mb 50 image.png
```

Available providers: `litterbox.catbox.moe`, `temp.sh`, `blob.zip`, `cliupload.com`, `file.io`, `transfer.sh`, `0x0.st`.

For screenshots and small public images, prefer `litterbox.catbox.moe`; it returns direct image URLs that browsers can render inline. `temp.sh` may show an intermediate/download page instead.
