#!/usr/bin/env python3
"""Generate Chinese narration with Aliyun MaaS TTS and mux it into a video.

This script intentionally reads credentials only from environment variables.
It never stores API keys in generated deliverables.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import wave
from pathlib import Path


httpx = None


def die(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        die(
            f"Missing {name}. Ask the user to provide it, for example in PowerShell:\n"
            f"  $env:{name}='...'\n"
            "Do not ask the user to paste secrets into chat when an environment variable is possible."
        )
    return value


def find_ffmpeg(explicit: str | None) -> str:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return str(path)
        die(f"FFmpeg path does not exist: {explicit}")

    found = shutil.which("ffmpeg")
    if found:
        return found

    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        die(
            "Could not find ffmpeg. Install ffmpeg, add it to PATH, or install imageio-ffmpeg "
            "and rerun the script."
        )


def run(args: list[str], quiet: bool = False) -> None:
    proc = subprocess.run(args, text=True, capture_output=quiet)
    if proc.returncode != 0:
        if quiet:
            sys.stderr.write(proc.stdout)
            sys.stderr.write(proc.stderr)
        raise subprocess.CalledProcessError(proc.returncode, args)


def split_text(text: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        sentences = re.split(r"(?<=[。；！？!?])", paragraph)
        buf = ""
        for sentence in sentences:
            if not sentence.strip():
                continue
            if len(buf) + len(sentence) > max_chars and buf:
                chunks.append(buf.strip())
                buf = sentence
            else:
                buf += sentence
        if buf.strip():
            chunks.append(buf.strip())
    return chunks


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / float(wav.getframerate())


def ffprobe_duration(ffmpeg: str, path: Path) -> float:
    ffprobe = Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    if not ffprobe.exists():
        return 0.0
    proc = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
        capture_output=True,
    )
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return 0.0


def synthesize_aliyun(
    *,
    text: str,
    out_dir: Path,
    host: str,
    api_key: str,
    model: str,
    voice: str,
    instructions: str,
    max_chars: int,
) -> list[Path]:
    global httpx
    if httpx is None:
        try:
            import httpx as httpx_module

            httpx = httpx_module
        except ImportError:
            die("Missing dependency: httpx. Install it with `python -m pip install httpx`.")

    if not host.startswith(("http://", "https://")):
        host = "https://" + host
    endpoint = host.rstrip("/") + "/api/v1/services/aigc/multimodal-generation/generation"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    chunks = split_text(text, max_chars)
    if not chunks:
        die("Narration script is empty.")

    parts: list[Path] = []
    for index, chunk in enumerate(chunks, 1):
        payload = {
            "model": model,
            "input": {
                "text": chunk,
                "voice": voice,
                "language_type": "Chinese",
                "instructions": instructions,
                "optimize_instructions": True,
            },
        }
        response = httpx.post(endpoint, headers=headers, json=payload, timeout=120)
        if response.status_code >= 400:
            die(
                f"TTS request failed for model={model!r}, voice={voice!r}: "
                f"HTTP {response.status_code}\n{response.text[:1000]}"
            )
        data = response.json()
        audio = ((data.get("output") or {}).get("audio") or {})
        url = audio.get("url")
        if not url:
            die(f"TTS response did not include output.audio.url:\n{str(data)[:1000]}")

        out = out_dir / f"part_{index:02d}.wav"
        with httpx.stream("GET", url, timeout=120) as download:
            download.raise_for_status()
            with out.open("wb") as handle:
                for block in download.iter_bytes():
                    handle.write(block)
        parts.append(out)
        print(f"TTS part {index}/{len(chunks)}: {len(chunk)} chars -> {out}")
    return parts


def concat_audio(ffmpeg: str, parts: list[Path], out_wav: Path) -> None:
    list_file = out_wav.with_suffix(".concat.txt")
    list_file.write_text(
        "".join(f"file '{part.resolve().as_posix()}'\n" for part in parts),
        encoding="utf-8",
    )
    run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-ar",
            "24000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ]
    )


def fit_audio_to_target(ffmpeg: str, in_wav: Path, out_wav: Path, target_seconds: float) -> None:
    duration = wav_duration(in_wav)
    if target_seconds <= 0 or duration <= target_seconds:
        shutil.copyfile(in_wav, out_wav)
        print(f"Narration duration: {duration:.2f}s")
        return

    tempo = min(2.0, duration / target_seconds)
    run([ffmpeg, "-y", "-i", str(in_wav), "-filter:a", f"atempo={tempo:.5f}", str(out_wav)])
    print(f"Narration duration: {duration:.2f}s -> {wav_duration(out_wav):.2f}s")


def mux_video(ffmpeg: str, video: Path, audio: Path, output: Path, volume: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-af",
            f"volume={volume}",
            str(output),
        ]
    )
    run([ffmpeg, "-hide_banner", "-i", str(output), "-f", "null", "-"], quiet=True)


def extract_contact_sheet(ffmpeg: str, video: Path, output: Path, every_seconds: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fps = f"1/{every_seconds}"
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-vf",
            f"fps={fps},scale=480:-1,tile=5x5",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(output),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Dub a video with Chinese Aliyun MaaS TTS narration.")
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audio-output", type=Path)
    parser.add_argument("--model", default=os.environ.get("ALIYUN_TTS_MODEL", "qwen3-tts-flash"))
    parser.add_argument("--voice", default=os.environ.get("ALIYUN_TTS_VOICE", "Cherry"))
    parser.add_argument("--host", default=os.environ.get("ALIYUN_MAAS_HOST"))
    parser.add_argument("--api-key", default=os.environ.get("ALIYUN_MAAS_API_KEY"))
    parser.add_argument("--ffmpeg", default=os.environ.get("FFMPEG_EXE"))
    parser.add_argument("--target-seconds", type=float, default=0)
    parser.add_argument("--volume", type=float, default=1.12)
    parser.add_argument("--max-chars", type=int, default=520)
    parser.add_argument(
        "--instructions",
        default=(
            "成熟自然的中文普通话女声，适合项目汇报和宣传片解说。"
            "吐字清晰、语气沉稳、有亲和力，不要机械，不要夸张。"
            "遇到技术名词保持自然停顿，整体节奏中等略快。"
        ),
    )
    parser.add_argument("--contact-sheet", type=Path, help="Optional path to write a video contact sheet.")
    args = parser.parse_args()

    if not args.video.exists():
        die(f"Video not found: {args.video}")
    if not args.script.exists():
        die(f"Narration script not found: {args.script}")

    api_key = args.api_key or require_env("ALIYUN_MAAS_API_KEY")
    host = args.host or require_env("ALIYUN_MAAS_HOST")
    ffmpeg = find_ffmpeg(args.ffmpeg)

    if args.contact_sheet:
        extract_contact_sheet(ffmpeg, args.video, args.contact_sheet, every_seconds=5)
        print(f"Contact sheet written: {args.contact_sheet}")

    text = args.script.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="video-narration-tts-") as temp:
        temp_dir = Path(temp)
        parts = synthesize_aliyun(
            text=text,
            out_dir=temp_dir,
            host=host,
            api_key=api_key,
            model=args.model,
            voice=args.voice,
            instructions=args.instructions,
            max_chars=args.max_chars,
        )
        raw = temp_dir / f"raw-{uuid.uuid4().hex}.wav"
        fitted = temp_dir / f"fitted-{uuid.uuid4().hex}.wav"
        concat_audio(ffmpeg, parts, raw)

        target = args.target_seconds
        if target <= 0:
            video_duration = ffprobe_duration(ffmpeg, args.video)
            target = max(0.0, video_duration - 7.0) if video_duration else 0.0
        fit_audio_to_target(ffmpeg, raw, fitted, target)

        if args.audio_output:
            args.audio_output.parent.mkdir(parents=True, exist_ok=True)
            run([ffmpeg, "-y", "-i", str(fitted), "-c:a", "mp3", "-b:a", "192k", str(args.audio_output)])
            print(f"Audio written: {args.audio_output}")

        mux_video(ffmpeg, args.video, fitted, args.output, args.volume)
        print(f"Dubbed video written: {args.output}")


if __name__ == "__main__":
    main()
