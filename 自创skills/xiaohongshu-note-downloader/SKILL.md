---
name: xiaohongshu-note-downloader
description: Download publicly accessible Xiaohongshu note links into local title-named folders with HTML, README metadata, source URL, images, and videos. Use when the user provides a xiaohongshu.com note/explore/share link and asks to save, download, archive, or organize the note content locally, especially with pictures or video.
---

# Xiaohongshu Note Downloader

## Quick Start

Use `scripts/download_xhs_note.py` for the repeatable download workflow.

```powershell
python "C:\Users\23262\.codex\skills\xiaohongshu-note-downloader\scripts\download_xhs_note.py" "<xiaohongshu-url>" --output-dir "<target-folder>"
```

Default output directory, when the user does not specify one:

```text
D:\23262\xiaohongshu-hot-top3
```

The script creates one subfolder per note. The subfolder name is the Xiaohongshu note title, sanitized for Windows filenames. If the title already exists, it appends a short note id or numeric suffix.

## Workflow

1. Run the script with the user-provided Xiaohongshu URL and requested output directory.
2. Report the generated `index.html` path, image count, and any missing fields.
3. If the script says no image or video metadata was found, explain that Xiaohongshu may require login/front-end signed APIs for that link and preserve the source URL anyway.

## Output Contract

Each note folder should contain:

```text
<title>/
+-- index.html
+-- README.md
+-- source-url.txt
+-- images/
    +-- image-01.jpg
    +-- ...
+-- videos/
    +-- video-01.mp4
    +-- ...
```

`index.html` should be directly openable and use local relative image paths.

## Notes

- Prefer the script over reimplementing parsing logic.
- The script extracts public HTML metadata such as `og:title`, `description`, `og:url`, `og:image`, and `og:video`; it also scans public HTML for direct `.mp4` URLs.
- Do not promise full note body or comments when the public HTML only exposes title, description, and images.
- Keep the original link in `source-url.txt` even when extraction is partial.
