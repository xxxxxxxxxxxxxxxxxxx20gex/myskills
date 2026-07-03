# Aliyun MaaS Qwen TTS Notes

Use these notes only when troubleshooting Aliyun MaaS/Qwen TTS calls.

## Endpoint Shape

For the MaaS host form:

```text
https://<host>/api/v1/services/aigc/multimodal-generation/generation
```

Send:

```json
{
  "model": "qwen3-tts-flash",
  "input": {
    "text": "旁白文本",
    "voice": "Cherry",
    "language_type": "Chinese",
    "instructions": "自然清晰的中文项目汇报旁白。",
    "optimize_instructions": true
  }
}
```

Use header:

```text
Authorization: Bearer <ALIYUN_MAAS_API_KEY>
Content-Type: application/json
```

The response normally contains:

```json
{
  "status_code": 200,
  "output": {
    "audio": {
      "url": "https://..."
    }
  }
}
```

Download `output.audio.url`; it is temporary.

## Useful Models And Voices

Start with:

- `qwen3-tts-flash`
- `Cherry`

Fallbacks observed in compatible endpoints:

- `qwen-tts-2025-05-22`
- voices: `Cherry`, `Serena`, `Ethan`, `Chelsie`, `Dylan`, `Jada`, `Sunny`

If `qwen3-tts-instruct-flash` returns `AccessDenied.Unpurchased`, use `qwen3-tts-flash` or ask the user to enable the model.

## Common Errors

- `404` on `/compatible-mode/v1/audio/speech`: the endpoint supports OpenAI-compatible model listing/chat routes but not the OpenAI audio speech route. Use the multimodal generation endpoint above.
- `AccessDenied.Unpurchased`: model is visible but not enabled or purchased for the account.
- `InvalidParameter ... input.voice`: the selected model supports a restricted voice list; switch to one of the accepted voices from the error.
