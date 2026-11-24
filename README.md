# Vidora - AI Video Assistant

Vidora turns a meeting recording, lecture or YouTube video into something you can read and query. Give it a YouTube URL or a local audio / video file and it transcribes the audio, writes a title and summary, pulls out action items, key decisions and open questions, and lets you chat with the content.

## Features

- **Any source:** YouTube URLs (downloaded with `yt-dlp`) or local audio and video files.
- **Transcription:** local [Whisper](https://github.com/openai/whisper) for English. Hinglish audio is transcribed and translated to English with the Sarvam speech-to-text-translate API.
- **Meeting intelligence:** title, summary, action items, key decisions and open questions, generated with Mistral (`mistral-small-latest`) through LangChain.
- **Chat with the video:** a RAG chain over the transcript, using `all-MiniLM-L6-v2` embeddings and ChromaDB.
- **Streamlit UI** with a step-by-step pipeline status, plus a CLI entry point.

## How it works

```text
source -> audio_processor (download, convert to WAV, 10-minute chunks)
       -> transcriber (Whisper or Sarvam)
       -> summarizer + extractor (Mistral)
       -> vector_store + rag_engine (ChromaDB, sentence-transformers)
```

## Web app and API

Requirements: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 20.9 or newer with npm, and FFmpeg on your `PATH`.

```bash
uv sync
npm --prefix frontend install
python run.py
```

`python run.py` starts the FastAPI service (<http://127.0.0.1:8000/health>) and the Next.js web app (<http://localhost:3000>). If either service fails to start or stops, the command says which one and exits. The web app shows a service-unavailable notice when it cannot reach the API. Set `VIDORA_API_URL` to point the web app at a different API address.

Run the backend tests with `uv run pytest` and the frontend checks with `npm --prefix frontend run lint`.

## Run the Streamlit app and CLI

Requirements: Python 3.13 and [FFmpeg](https://ffmpeg.org) on your `PATH`.

1. Create a `.env` file:

   ```env
   MISTRAL_API_KEY=your_key
   # optional
   SARVAM_API_KEY=your_key          # needed for Hinglish
   WHISPER_MODEL=small              # tiny, base, small, medium, large
   SARVAM_STT_MODEL=saaras:v2.5
   ```

2. Install and run:

   ```bash
   uv venv
   uv pip install -r requirements.txt
   uv run streamlit run app.py      # web UI
   uv run python main.py            # or the CLI
   ```

## Project structure

```text
app.py                 Streamlit UI
main.py                Pipeline and CLI entry point
core/
  transcriber.py       Whisper and Sarvam transcription
  summarizer.py        Title and summary
  extractor.py         Action items, decisions, questions
  vector_store.py      ChromaDB vector store
  rag_engine.py        Question answering over the transcript
utils/
  audio_processor.py   Download, convert and chunk audio
```

## Tech stack

Python, Streamlit, LangChain, Mistral AI, OpenAI Whisper, Sarvam AI, ChromaDB, sentence-transformers, yt-dlp, pydub.
