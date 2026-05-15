#!/usr/bin/env python3
import argparse
import html
import json
import mimetypes
import re
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(r"D:\23262\douyin")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch_bytes(url: str, referer: str | None = None) -> tuple[bytes, str]:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    return (name or "douyin-video")[:120].rstrip(" .")


def unique_dir(base: Path, title: str, aweme_id: str) -> Path:
    candidate = base / sanitize_filename(title)
    if not candidate.exists():
        return candidate
    if aweme_id:
        candidate = base / sanitize_filename(f"{title} {aweme_id}")
        if not candidate.exists():
            return candidate
    index = 2
    while True:
        candidate = base / sanitize_filename(f"{title} {index}")
        if not candidate.exists():
            return candidate
        index += 1


def note_id_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if qs.get("modal_id"):
        return qs["modal_id"][0]
    match = re.search(r"/video/([^/?#]+)", parsed.path)
    return match.group(1) if match else ""


def extract_flight_parts(page: str) -> list[str]:
    parts = []
    for match in re.finditer(r'self\.__pace_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', page):
        try:
            parts.append(json.loads('"' + match.group(1) + '"'))
        except json.JSONDecodeError:
            pass
    return parts


def extract_json_object(text: str, key: str) -> dict:
    idx = text.find(f'"{key}"')
    if idx == -1:
        raise ValueError(f"{key} not found")
    colon = text.find(":", idx)
    start = text.find("{", colon)
    depth = 0
    in_string = False
    escaped = False
    for pos in range(start, len(text)):
        ch = text[pos]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : pos + 1])
    raise ValueError(f"{key} object was not complete")


def extract_video_detail(page: str, aweme_id: str) -> dict:
    for part in extract_flight_parts(page):
        decoded = urllib.parse.unquote(part)
        if '"videoDetail"' in decoded and (not aweme_id or aweme_id in decoded):
            return extract_json_object(decoded, "videoDetail")
    raise ValueError("videoDetail not found in SSR data")


def media_ext(content_type: str, fallback: str) -> str:
    ext = mimetypes.guess_extension(content_type.split(";", 1)[0]) or fallback
    return ".jpg" if ext == ".jpe" else ext


def download(url: str, folder: Path, name: str, fallback_ext: str) -> tuple[str, int]:
    data, content_type = fetch_bytes(url, referer="https://www.douyin.com/")
    filename = name + media_ext(content_type, fallback_ext)
    path = folder / filename
    path.write_bytes(data)
    return filename, len(data)


def first_src(items) -> str:
    if not items:
        return ""
    item = items[0]
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("src") or item.get("url") or ""
    return ""


def video_url(video: dict) -> str:
    for bitrate in video.get("bitRateList") or []:
        url = first_src(bitrate.get("playAddr"))
        if url:
            return url
    return first_src(video.get("playAddr"))


def render_html(vd: dict, source_url: str, video_file: str | None, covers: list[tuple[str, str]], chapters: list[tuple[dict, str]]) -> str:
    title = vd.get("itemTitle") or vd.get("desc") or vd.get("awemeId") or "douyin-video"
    desc = vd.get("desc") or ""
    cover_html = "".join(
        f'<figure><img src="images/{html.escape(filename)}" alt="{html.escape(label)}"><figcaption>{html.escape(label)}</figcaption></figure>'
        for label, filename in covers
    )
    chapter_html = "".join(
        f'<figure><img src="images/{html.escape(filename)}" alt="{html.escape(ch.get("desc", ""))}"><figcaption>{html.escape(ch.get("desc", ""))} | {int(ch.get("timestamp", 0))/1000:.1f}s<br>{html.escape(ch.get("detail", ""))}</figcaption></figure>'
        for ch, filename in chapters
    )
    video_html = f'<figure><video src="videos/{html.escape(video_file)}" controls preload="metadata"></video><figcaption>Video</figcaption></figure>' if video_file else ""
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; background: #f6f6f7; color: #1f2328; }}
    header {{ background: #fff; border-bottom: 1px solid #e8e8eb; padding: 28px 32px; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 24px 18px 48px; }}
    h1 {{ margin: 0 0 12px; font-size: 30px; line-height: 1.25; }}
    .desc {{ white-space: pre-wrap; font-size: 16px; line-height: 1.8; color: #333; background: #fff; border: 1px solid #e8e8eb; border-radius: 8px; padding: 18px; }}
    .meta {{ color: #666; line-height: 1.8; font-size: 14px; }}
    figure {{ margin: 18px 0; background: #fff; border: 1px solid #e8e8eb; border-radius: 8px; padding: 12px; }}
    img, video {{ display: block; max-width: 100%; height: auto; margin: 0 auto; border-radius: 4px; }}
    figcaption {{ color: #666; font-size: 13px; line-height: 1.6; margin-top: 10px; }}
    a {{ color: #2563eb; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="meta">Saved at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>Source: <a href="{html.escape(source_url)}">{html.escape(source_url)}</a></div>
  </header>
  <main>
    <section class="desc">{html.escape(desc)}</section>
    {video_html}
    {cover_html}
    <h2>Chapters</h2>
    {chapter_html}
  </main>
</body>
</html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public Douyin SSR video media and metadata.")
    parser.add_argument("url", help="Douyin URL")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Parent folder for title-named video folder")
    args = parser.parse_args()

    aweme_id = note_id_from_url(args.url)
    page, _ = fetch_bytes(args.url)
    vd = extract_video_detail(page.decode("utf-8", errors="replace"), aweme_id)
    title = vd.get("itemTitle") or vd.get("desc") or vd.get("awemeId") or "douyin-video"
    outdir = unique_dir(Path(args.output_dir), title, vd.get("awemeId") or aweme_id)
    images_dir = outdir / "images"
    videos_dir = outdir / "videos"
    images_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    cover_downloads = []
    for label, url in [
        ("cover", vd.get("video", {}).get("cover")),
        ("origin-cover", vd.get("video", {}).get("originCover")),
    ]:
        if url:
            filename, _ = download(url, images_dir, label, ".jpg")
            cover_downloads.append((label, filename))

    chapter_downloads = []
    for index, chapter in enumerate(vd.get("chapterInfo", {}).get("list", []), 1):
        if chapter.get("url"):
            filename, _ = download(chapter["url"], images_dir, f"chapter-{index:02d}", ".jpg")
            chapter_downloads.append((chapter, filename))

    video_file = None
    video_size = 0
    url = video_url(vd.get("video", {}))
    if url:
        video_file, video_size = download(url, videos_dir, "video-01", ".mp4")

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "index.html").write_text(render_html(vd, args.url, video_file, cover_downloads, chapter_downloads), encoding="utf-8")
    (outdir / "README.md").write_text(
        f"# {title}\n\n"
        f"Source URL: {args.url}\n\n"
        f"Aweme ID: {vd.get('awemeId')}\n\n"
        f"Description:\n{vd.get('desc') or ''}\n\n"
        f"Video downloaded: {bool(video_file)}\n"
        f"Video size: {video_size}\n"
        f"Covers downloaded: {len(cover_downloads)}\n"
        f"Chapters downloaded: {len(chapter_downloads)}\n",
        encoding="utf-8",
    )
    (outdir / "source-url.txt").write_text(args.url + "\n", encoding="utf-8")
    (outdir / "videoDetail.json").write_text(json.dumps(vd, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"output_dir={outdir}")
    print(f"title={title}")
    print(f"aweme_id={vd.get('awemeId')}")
    print(f"video_downloaded={bool(video_file)}")
    print(f"video_size={video_size}")
    print(f"covers_downloaded={len(cover_downloads)}")
    print(f"chapters_downloaded={len(chapter_downloads)}")
    print(f"index_html={outdir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
