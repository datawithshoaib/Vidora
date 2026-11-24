# Vidora - AI Video Assistant

Vidora turns a YouTube video or an uploaded audio/video file into something you can read. Paste a link or upload a file and it transcribes the audio in English, then writes a title, summary, action items, key decisions and open questions. Everything runs locally as a single-user tool.

## Features

- **YouTube analysis:** submit a YouTube URL; audio is downloaded with `yt-dlp`.
- **File uploads:** upload an audio or video file (MP3, WAV, M4A, MP4, MOV, WebM and more) up to 500 MB with the file picker or by dragging it onto the page. Uploads go through the same transcription and notes pipeline.
- **Background jobs:** each submission is a fresh job with visible progress (queued, downloading, transcribing, analyzing, then completed or failed). Jobs and results are stored in SQLite and survive restarts.
- **History:** a sidebar lists every analysis (including failed ones) with its status and date, newest first. Open a past one to read it again, or delete it (with confirmation) to remove its record, transcript, notes and any retained files. Deleting a job that is still queued or processing is refused until it finishes.
- **Chat with an analysis:** ask questions about a completed analysis and get answers grounded in its transcript (Mistral). Follow-ups use the earlier turns as context, and the conversation is saved with the analysis, so it is still there after a reload or restart and is deleted with the analysis. Short transcripts are sent whole; long ones send only the most relevant passages, found by keyword matching (no vector index to maintain).
- **English transcription:** local [Whisper](https://github.com/openai/whisper).
- **Notes:** title, summary, action items, key decisions and open questions generated with Mistral (`mistral-small-latest`) through LangChain.
- **Private by default:** downloaded audio and uploaded files live in a job-scoped temp folder and are deleted when the job finishes or fails, including rejected or partial uploads.

## Setup

Requirements: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 20.9 or newer with npm, and [FFmpeg](https://ffmpeg.org) on your `PATH`.

1. Create a `.env` file in the repository root:

   ```env
   MISTRAL_API_KEY=your_key
   # optional
   WHISPER_MODEL=small        # tiny, base, small, medium, large
   VIDORA_DATA_DIR=data       # where the SQLite database and temp files live
   VIDORA_MAX_UPLOAD_MB=500   # maximum upload size in MB
   ```

2. Install and run:

   ```bash
   uv sync
   npm --prefix frontend install
   python run.py
   ```

`python run.py` starts the FastAPI service (<http://127.0.0.1:8000>) and the Next.js web app (<http://localhost:3000>). If either stops, the command says which one and exits. Set `VIDORA_API_URL` to point the web app's server at a different API address, and `NEXT_PUBLIC_VIDORA_API_URL` (default `http://127.0.0.1:8000`) for the address the browser uploads to. Uploads go from the browser straight to the API (CORS allows `localhost:3000`) so large files are not buffered by the Next.js server. The first analysis downloads the Whisper model, which can take a while.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/jobs` | Body `{"url": "<YouTube URL>"}`. Returns `202` with a queued job, or `422` for an invalid URL. |
| `POST` | `/jobs/upload` | Multipart form with a `file` field. Returns `202` with a queued job, `415` for an unsupported type, or `413` when over the size limit. The file is streamed to disk, never held in memory. |
| `GET` | `/jobs` | History: all jobs newest first, with `status`, `created_at`, `source`, and the analysis `title` when completed. |
| `GET` | `/jobs/{id}` | Job `status` (`queued`, `processing`, `completed`, `failed`), current `step`, `error`, and `analysis_id` when done. |
| `GET` | `/analyses/{id}` | Title, summary, action items, key decisions, open questions and transcript. |
| `GET` | `/analyses/{id}/chat` | Saved questions and answers, oldest first. `404` if the analysis is unknown, `409` if it is still being processed. |
| `POST` | `/analyses/{id}/chat` | Body `{"question": "..."}`. Returns the saved question and answer. `422` for an empty question, `404`/`409` as above, `502` if the model call fails (nothing is saved). |
| `DELETE` | `/jobs/{id}` | Deletes the job, its analysis and retained artifacts. `204`; `404` if unknown; `409` while queued or processing. |
| `DELETE` | `/analyses/{id}` | Deletes an analysis and the job that produced it. `204` or `404`. |
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
  retrieval.py         Picks transcript passages for a chat question
  sources.py           YouTube URL validation
  uploads.py           Streaming upload validation and storage
  store.py             SQLite storage for jobs, analyses and chat
tests/                 API workflow tests
frontend/              Next.js app (shadcn/ui, Tailwind CSS)
```

## Tech stack

Python, FastAPI, SQLite, LangChain, Mistral AI, OpenAI Whisper, yt-dlp, pydub, Next.js, shadcn/ui, Tailwind CSS.
