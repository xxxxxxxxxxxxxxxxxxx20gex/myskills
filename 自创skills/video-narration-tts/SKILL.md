---
name: video-narration-tts
description: Rewrite narration to match a video's actual visuals, generate natural Chinese text-to-speech with Aliyun MaaS/Qwen TTS, and mux the audio into an MP4. Use when a user asks to add, improve, replace, or synchronize Chinese voiceover/narration for a video, especially when they provide an Aliyun/DashScope/MaaS endpoint or want a reusable video dubbing workflow. Also use when the user asks to turn this video narration process into a repeatable workflow.
---

# Video Narration TTS

Use this skill to produce a video with natural Chinese narration that matches the on-screen content.

## Workflow

1. Inspect the source video before writing narration.
   - Use `ffmpeg`/`ffprobe` if available.
   - Extract contact sheets or keyframes at 2-5 second intervals.
   - Identify the actual slide/page order, visible headings, and major visual claims.

2. Rewrite the narration for visual correspondence.
   - Follow the screen order. Say what the viewer is seeing now or about to see.
   - Keep technical implementation details brief unless the video actually shows them.
   - If the video is a proposal, report, or slide-style demo, avoid narrating invisible UI operations such as "open the workflow" or "click save" unless those actions are visible.
   - Preserve user-required content, but compress or reframe it so it fits the visuals and duration.
   - Target narration audio to end 5-8 seconds before the video ends unless the user requests full-length narration.

3. Check credentials before calling TTS.
   - For Aliyun MaaS/Qwen TTS, require:
     - `ALIYUN_MAAS_API_KEY`
     - `ALIYUN_MAAS_HOST`
   - Optional:
     - `ALIYUN_TTS_MODEL`, default `qwen3-tts-flash`
     - `ALIYUN_TTS_VOICE`, default `Cherry`
     - `FFMPEG_EXE`
   - If credentials are missing, tell the user exactly which environment variables to set. Prefer environment variables over asking the user to paste secrets in chat.

4. Generate TTS and mux the MP4.
   - Prefer `scripts/dub_video_with_tts.py` for repeatability.
   - Save final user-facing deliverables in the active workspace `outputs/` directory when applicable.
   - Export both the dubbed MP4 and the standalone narration audio when useful.
   - Validate the final MP4 by decoding it with ffmpeg.

## Script

Use the bundled script:

```powershell
python C:\Users\WUJIEAI\.codex\skills\video-narration-tts\scripts\dub_video_with_tts.py `
  --video "C:\path\input.mp4" `
  --script "C:\path\narration.txt" `
  --output "C:\path\outputs\dubbed.mp4" `
  --audio-output "C:\path\outputs\narration.mp3"
```

The script:

- Reads credentials only from arguments or environment variables.
- Fails with a clear message if `ALIYUN_MAAS_API_KEY` or `ALIYUN_MAAS_HOST` is missing.
- Calls Aliyun MaaS non-realtime multimodal generation endpoint:
  `/api/v1/services/aigc/multimodal-generation/generation`
- Splits long narration into chunks, downloads returned WAV URLs, concatenates audio, optionally fits duration, and muxes with the original video.
- Copies the original video stream to preserve video quality.

## Environment Setup To Request From User

If the user has not provided credentials, ask them to set:

```powershell
$env:ALIYUN_MAAS_API_KEY="your-api-key"
$env:ALIYUN_MAAS_HOST="your-host, for example llm-xxxx.cn-beijing.maas.aliyuncs.com"
```

Optional voice/model overrides:

```powershell
$env:ALIYUN_TTS_MODEL="qwen3-tts-flash"
$env:ALIYUN_TTS_VOICE="Cherry"
```

If a model returns `AccessDenied.Unpurchased`, try a model listed by the user's endpoint or ask the user to enable that model. Known useful fallbacks include `qwen-tts-2025-05-22` and voices such as `Cherry`, `Serena`, `Ethan`, `Chelsie`, `Dylan`, `Jada`, and `Sunny`, depending on endpoint support.

## Narration Guidance

For slide-style proposal/report videos:

- Open with the product/system name and purpose.
- Match sections to visible headings.
- Use numbers only when they appear on screen or are provided by the user.
- Put technology in one concise support paragraph unless the video shows technical UI.
- End with the exact deliverable/result the video shows: interaction, learning tasks, communication materials, activity data, report visuals, or a digital experience entrance.

For screen-recorded workflows:

- Narrate visible operations step by step.
- Use the user's technical terms exactly where they appear.
- Avoid overexplaining backend architecture while UI actions are happening.

## Security

Never write API keys into `SKILL.md`, output files, final responses, or checked-in scripts. If a user pasted a key into chat, do not repeat it; use it only for the immediate local call if necessary and recommend rotating it after the task.
