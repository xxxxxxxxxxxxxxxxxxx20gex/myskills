#!/usr/bin/env python3
import argparse
import html
import mimetypes
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(r"D:\23262\xiaohongshu-hot-top3")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
)
XHS_SUFFIX = " - \u5c0f\u7ea2\u4e66"


def fetch_bytes(url: str, referer: str | None = None) -> tuple[bytes, str]:
    headers = {"User-Agent": USER_AGENT}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), resp.headers.get("Content-Type", "")


def meta_values(page: str, name: str) -> list[str]:
    patterns = [
        rf'<meta\s+name="{re.escape(name)}"\s+content="([^"]*)"',
        rf'<meta\s+property="{re.escape(name)}"\s+content="([^"]*)"',
        rf'<meta\s+content="([^"]*)"\s+name="{re.escape(name)}"',
        rf'<meta\s+content="([^"]*)"\s+property="{re.escape(name)}"',
    ]
    values: list[str] = []
    for pattern in patterns:
        values.extend(html.unescape(value).strip() for value in re.findall(pattern, page, flags=re.IGNORECASE))
    seen = set()
    return [value for value in values if value and not (value in seen or seen.add(value))]


def meta_content(page: str, name: str) -> str:
    values = meta_values(page, name)
    return values[0] if values else ""


def video_urls_from_page(page: str) -> list[str]:
    urls = []
    for name in ["og:video", "og:video:url", "og:video:secure_url"]:
        urls.extend(meta_values(page, name))
    urls.extend(re.findall(r'https?://[^"\\<> ]+\.mp4[^"\\<> ]*', page, flags=re.IGNORECASE))
    seen = set()
    return [url for url in urls if url and not (url in seen or seen.add(url))]


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    if not name or name.upper() in reserved:
        return "xiaohongshu-note"
    return name[:120].rstrip(" .")


def unique_dir(base: Path, title: str, note_id: str) -> Path:
    candidate = base / sanitize_filename(title)
    if not candidate.exists():
        return candidate
    if note_id:
        candidate = base / sanitize_filename(f"{title} {note_id}")
        if not candidate.exists():
            return candidate
    index = 2
    while True:
        candidate = base / sanitize_filename(f"{title} {index}")
        if not candidate.exists():
            return candidate
        index += 1


def note_id_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    match = re.search(r"/(?:explore|discovery/item)/([^/?#]+)", path)
    return match.group(1) if match else ""


def media_extension(content_type: str, fallback: str) -> str:
    media_type = content_type.split(";", 1)[0]
    ext = mimetypes.guess_extension(media_type) or fallback
    return ".jpg" if ext == ".jpe" else ext


def download_media(urls: list[str], folder: Path, prefix: str, fallback_ext: str) -> list[tuple[str | None, str, str | int]]:
    folder.mkdir(parents=True, exist_ok=True)
    downloaded: list[tuple[str | None, str, str | int]] = []
    for index, url in enumerate(urls, 1):
        try:
            data, content_type = fetch_bytes(url, referer="https://www.xiaohongshu.com/")
            filename = f"{prefix}-{index:02d}{media_extension(content_type, fallback_ext)}"
            (folder / filename).write_bytes(data)
            downloaded.append((filename, url, len(data)))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            downloaded.append((None, url, str(exc)))
    return downloaded


def render_html(
    title: str,
    description: str,
    source_url: str,
    canonical: str,
    downloaded_images: list[tuple[str | None, str, str | int]],
    downloaded_videos: list[tuple[str | None, str, str | int]],
) -> str:
    videos = []
    for index, (name, url, info) in enumerate(downloaded_videos, 1):
        if name:
            videos.append(
                f'<figure><video src="videos/{html.escape(name)}" controls playsinline preload="metadata"></video>'
                f'<figcaption>Video {index} | Source CDN: <a href="{html.escape(url)}">original video link</a></figcaption></figure>'
            )
        else:
            videos.append(
                f'<p class="warn">Video {index} download failed: {html.escape(str(info))}<br>'
                f'<a href="{html.escape(url)}">original video link</a></p>'
            )

    figures = []
    for index, (name, url, info) in enumerate(downloaded_images, 1):
        if name:
            figures.append(
                f'<figure><img src="images/{html.escape(name)}" alt="Xiaohongshu image {index}">'
                f'<figcaption>Image {index} | Source CDN: <a href="{html.escape(url)}">original image link</a></figcaption></figure>'
            )
        else:
            figures.append(
                f'<p class="warn">Image {index} download failed: {html.escape(str(info))}<br>'
                f'<a href="{html.escape(url)}">original image link</a></p>'
            )

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; background: #f6f6f7; color: #1f2328; }}
    header {{ background: #fff; border-bottom: 1px solid #e8e8eb; padding: 28px 32px; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 24px 18px 48px; }}
    h1 {{ margin: 0 0 12px; font-size: 30px; line-height: 1.25; }}
    .desc {{ white-space: pre-wrap; font-size: 16px; line-height: 1.8; color: #333; background: #fff; border: 1px solid #e8e8eb; border-radius: 8px; padding: 18px; }}
    .meta {{ color: #666; line-height: 1.8; font-size: 14px; }}
    a {{ color: #2563eb; }}
    figure {{ margin: 18px 0; background: #fff; border: 1px solid #e8e8eb; border-radius: 8px; padding: 12px; }}
    img, video {{ display: block; max-width: 100%; height: auto; margin: 0 auto; border-radius: 4px; }}
    figcaption {{ color: #666; font-size: 13px; line-height: 1.6; margin-top: 10px; word-break: break-all; }}
    .warn {{ background: #fff7ed; border: 1px solid #fed7aa; color: #7c2d12; padding: 12px; border-radius: 8px; }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="meta">Saved at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br>Source: <a href="{html.escape(source_url)}">original link</a><br>Canonical: <a href="{html.escape(canonical)}">{html.escape(canonical)}</a></div>
  </header>
  <main>
    <section class="desc">{html.escape(description)}</section>
    {''.join(videos)}
    {''.join(figures)}
  </main>
</body>
</html>'''


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public Xiaohongshu note metadata, images, and videos.")
    parser.add_argument("url", help="Xiaohongshu note URL")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Parent folder for title-named note folder")
    args = parser.parse_args()

    source_url = args.url
    base = Path(args.output_dir)
    base.mkdir(parents=True, exist_ok=True)

    page_bytes, _ = fetch_bytes(source_url)
    page = page_bytes.decode("utf-8", errors="replace")

    title = meta_content(page, "og:title") or meta_content(page, "twitter:title") or "xiaohongshu-note"
    title = title.removesuffix(XHS_SUFFIX).strip() or "xiaohongshu-note"
    description = meta_content(page, "description") or meta_content(page, "og:description")
    canonical = meta_content(page, "og:url") or source_url
    note_id = note_id_from_url(source_url)

    image_urls = meta_values(page, "og:image")
    video_urls = video_urls_from_page(page)

    outdir = unique_dir(base, title, note_id)
    outdir.mkdir(parents=True, exist_ok=True)
    downloaded_images = download_media(image_urls, outdir / "images", "image", ".jpg")
    downloaded_videos = download_media(video_urls, outdir / "videos", "video", ".mp4")

    (outdir / "index.html").write_text(
        render_html(title, description, source_url, canonical, downloaded_images, downloaded_videos),
        encoding="utf-8",
    )
    (outdir / "README.md").write_text(
        f"# {title}\n\n"
        f"Source URL: {source_url}\n\n"
        f"Canonical URL: {canonical}\n\n"
        f"Description:\n{description}\n\n"
        f"Images found: {len(image_urls)}\n"
        f"Images downloaded: {sum(1 for name, _, _ in downloaded_images if name)}\n"
        f"Videos found: {len(video_urls)}\n"
        f"Videos downloaded: {sum(1 for name, _, _ in downloaded_videos if name)}\n\n"
        f"Saved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        encoding="utf-8",
    )
    (outdir / "source-url.txt").write_text(source_url + "\n", encoding="utf-8")

    print(f"output_dir={outdir}")
    print(f"title={title}")
    print(f"description={description}")
    print(f"images_found={len(image_urls)}")
    print(f"images_downloaded={sum(1 for name, _, _ in downloaded_images if name)}")
    print(f"videos_found={len(video_urls)}")
    print(f"videos_downloaded={sum(1 for name, _, _ in downloaded_videos if name)}")
    print(f"index_html={outdir / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
