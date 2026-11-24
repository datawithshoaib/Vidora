# Vidora - AI Video Assistant

Vidora turns a YouTube video into something you can read. Paste a link and it transcribes the audio in English, then writes a title, summary, action items, key decisions and open questions. Everything runs locally as a single-user tool.

## Features

- **YouTube analysis:** submit a YouTube URL; audio is downloaded with `yt-dlp`.
- **Background jobs:** each submission is a fresh job with visible progress (queued, downloading, transcribing, analyzing, then completed or failed). Jobs and results are stored in SQLite and survive restarts.
- **English transcription:** local [Whisper](https://github.com/openai/whisper).
- **Notes:** title, summary, action items, key decisions and open questions generated with Mistral (`mistral-small-latest`) through LangChain.
- **Private by default:** downloaded audio lives in a job-scoped temp folder and is deleted when the job finishes or fails.

## Setup

Requirements: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 20.9 or newer with npm, and [FFmpeg](https://ffmpeg.org) on your `PATH`.

1. Create a `.env` file in the repository root:

   ```env
   MISTRAL_API_KEY=your_key
   # optional
   WHISPER_MODEL=small        # tiny, base, small, medium, large
   VIDORA_DATA_DIR=data       # where the SQLite database and temp files live
   ```

2. Install and run:

   ```bash
   uv sync
   npm --prefix frontend install
   python run.py
   ```

`python run.py` starts the FastAPI service (<http://127.0.0.1:8000>) and the Next.js web app (<http://localhost:3000>). If either stops, the command says which one and exits. Set `VIDORA_API_URL` to point the web app at a different API address. The first analysis downloads the Whisper model, which can take a while.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/jobs` | Body `{"url": "<YouTube URL>"}`. Returns `202` with a queued job, or `422` for an invalid URL. |
| `GET` | `/jobs/{id}` | Job `status` (`queued`, `processing`, `completed`, `failed`), current `step`, `error`, and `analysis_id` when done. |
| `GET` | `/analyses/{id}` | Title, summary, action items, key decisions, open questions and transcript. |
| `GET` | `/health` | Service check. |

## Development

```bash
uv run pytest                      # backend tests (no network, no Whisper, no LLM)
npm --prefix frontend run lint
npm --prefix frontend run build
```

Backend tests exercise the API through FastAPI's test client with fake download, transcription and AI steps.

## Project structure

```text
run.py                 Starts the API and web app together
api/
  main.py              FastAPI app factory and routes
  pipeline.py          Job orchestration and step interfaces
  adapters.py          yt-dlp, Whisper and Mistral implementations
  sources.py           YouTube URL validation
  store.py             SQLite storage for jobs and analyses
tests/                 API workflow tests
frontend/              Next.js app (shadcn/ui, Tailwind CSS)
```

## Tech stack

Python, FastAPI, SQLite, LangChain, Mistral AI, OpenAI Whisper, yt-dlp, pydub, Next.js, shadcn/ui, Tailwind CSS.
