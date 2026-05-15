---
name: douyin-video-downloader
description: Download publicly accessible Douyin links into local title-named folders with HTML, README metadata, source URL, video, cover images, chapter images, and raw videoDetail JSON. Use when the user provides a douyin.com jingxuan/video/share link and asks to save, download, archive, test, or organize the Douyin content locally.
---

# Douyin Video Downloader

## Quick Start

Use `scripts/download_douyin_video.py` for the repeatable download workflow.

```powershell
python "C:\Users\23262\.codex\skills\douyin-video-downloader\scripts\download_douyin_video.py" "<douyin-url>" --output-dir "<target-folder>"
```

Default output directory, when the user does not specify one:

```text
D:\23262\douyin
```

The script creates one subfolder per video. The subfolder name is the Douyin item title, sanitized for Windows filenames. If the title already exists, it appends the aweme id or a numeric suffix.

## Workflow

1. Run the script with the user-provided Douyin URL and requested output directory.
2. Report the generated `index.html` path, video size, cover count, chapter image count, and any missing fields.
3. If `videoDetail` is not found, explain that the page layout may have changed or the link may require login/front-end APIs; preserve the source URL if a partial output was created.

## Output Contract

Each video folder should contain:

```text
<title>/
+-- index.html
+-- README.md
+-- source-url.txt
+-- videoDetail.json
+-- images/
    +-- cover.jpg
    +-- origin-cover.jpg
    +-- chapter-01.jpg
    +-- ...
+-- videos/
    +-- video-01.mp4
```

`index.html` should be directly openable and use local relative image/video paths.

## Notes

- Prefer the script over reimplementing parsing logic.
- The script targets Douyin PC SSR React Flight data and extracts `videoDetail`.
- Supported URL shapes include `https://www.douyin.com/jingxuan?modal_id=...` and `/video/<id>` when the page exposes the same SSR data.
- Do not promise comments, private account data, or authenticated-only resources.
