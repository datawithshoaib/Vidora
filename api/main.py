import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.adapters import MistralAnalyzer, WhisperTranscriber, YoutubeFetcher
from api.pipeline import Analyzer, MediaFetcher, Pipeline, Runner, Transcriber
from api.sources import INVALID_URL_MESSAGE, is_youtube_video_url
from api.store import Store

DEFAULT_DATA_DIR = Path("data")


class JobRequest(BaseModel):
    url: str


class ThreadRunner:
    """Runs jobs on a small background thread pool (one at a time by default)."""

    def __init__(self, workers: int = 1) -> None:
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="vidora-job")

    def submit(self, fn) -> None:
        self._pool.submit(fn)


def create_app(
    data_dir: Path | None = None,
    fetcher: MediaFetcher | None = None,
    transcriber: Transcriber | None = None,
    analyzer: Analyzer | None = None,
    runner: Runner | None = None,
) -> FastAPI:
    load_dotenv()
    data_dir = Path(data_dir or os.getenv("VIDORA_DATA_DIR") or DEFAULT_DATA_DIR)
    store = Store(data_dir / "vidora.db")
    store.fail_unfinished_jobs("Job was interrupted because the service restarted.")
    pipeline = Pipeline(
        store=store,
        tmp_root=data_dir / "tmp",
        fetcher=fetcher or YoutubeFetcher(),
        transcriber=transcriber or WhisperTranscriber(),
        analyzer=analyzer or MistralAnalyzer(),
    )
    runner = runner or ThreadRunner()

    app = FastAPI(title="Vidora API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/jobs", status_code=202)
    def submit_job(request: JobRequest) -> dict:
        if not is_youtube_video_url(request.url):
            raise HTTPException(status_code=422, detail=INVALID_URL_MESSAGE)
        job = store.create_job("youtube", request.url.strip())
        runner.submit(lambda: pipeline.run(job["id"]))
        return job

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return job

    @app.get("/analyses/{analysis_id}")
    def get_analysis(analysis_id: str) -> dict:
        analysis = store.get_analysis(analysis_id)
        if analysis is None:
            raise HTTPException(status_code=404, detail="Analysis not found.")
        return analysis

    return app

