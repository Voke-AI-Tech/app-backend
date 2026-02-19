---
title: Voke AI Speech Evaluation API
emoji: 🎙️
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Voke AI Speech Evaluation API

FastAPI backend for evaluating spoken English — grammar, vocabulary, fluency, pronunciation, and filler words.

## Environment Variables

Set these as **Secrets** in your Hugging Face Space settings:

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Google Gemini API key |
| `MODEL` | No | Gemini model (default: `models/gemini-2.5-flash`) |
| `DEVICE` | No | `cpu` (default) or `cuda` |
| `COMPUTE_TYPE` | No | `int8` (recommended for CPU) or `float16` |
| `WHISPER_MODEL` | No | Whisper model size (default: `base`) |
| `BATCH_SIZE` | No | Processing batch size (default: `16`) |

## Local Development

```bash
cp .env.example .env
# Fill in your API keys in .env
pip install -r requirements.txt
python main.py
```
