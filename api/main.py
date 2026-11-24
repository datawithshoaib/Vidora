import logging
import os
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.adapters import (
    FfmpegPreparer,
    MistralAnalyzer,
    MistralAnswerer,
    WhisperTranscriber,
    YoutubeFetcher,
)
from api.pipeline import Analyzer, Answerer, MediaFetcher, Pipeline, Runner, Transcriber, UploadPreparer
from api.retrieval import select_context
from api.sources import INVALID_URL_MESSAGE, is_youtube_video_url
from api.store import Store
from api.uploads import DEFAULT_MAX_UPLOAD_MB, UploadError, receive_upload

logger = logging.getLogger("vidora.api")

DEFAULT_DATA_DIR = Path("data")


class JobRequest(BaseModel):
    url: str


class ChatRequest(BaseModel):
    question: str


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
    answerer: Answerer | None = None,
    runner: Runner | None = None,
    preparer: UploadPreparer | None = None,
    max_upload_bytes: int | None = None,
) -> FastAPI:
    load_dotenv()
    data_dir = Path(data_dir or os.getenv("VIDORA_DATA_DIR") or DEFAULT_DATA_DIR)
    store = Store(data_dir / "vidora.db")
    store.fail_unfinished_jobs("Job was interrupted because the service restarted.")
    shutil.rmtree(data_dir / "tmp", ignore_errors=True)  # leftovers from a crash
    if max_upload_bytes is None:
        max_upload_bytes = int(
            float(os.getenv("VIDORA_MAX_UPLOAD_MB") or DEFAULT_MAX_UPLOAD_MB) * 1024 * 1024
        )
    pipeline = Pipeline(
        store=store,
        tmp_root=data_dir / "tmp",
        fetcher=fetcher or YoutubeFetcher(),
        transcriber=transcriber or WhisperTranscriber(),
        analyzer=analyzer or MistralAnalyzer(),
        preparer=preparer or FfmpegPreparer(),
    )
    answerer = answerer or MistralAnswerer()
    runner = runner or ThreadRunner()

    app = FastAPI(title="Vidora API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
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

    @app.post("/jobs/upload", status_code=202)
    async def upload_job(request: Request) -> dict:
        job_id = uuid.uuid4().hex
        workdir = data_dir / "tmp" / job_id
        try:
            filename = await receive_upload(request, workdir, max_upload_bytes)
        except UploadError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)
        try:
            job = store.create_job("upload", filename, job_id=job_id)
        except Exception:
            shutil.rmtree(workdir, ignore_errors=True)
            raise
        runner.submit(lambda: pipeline.run(job_id))
        return job

    @app.get("/jobs")
    def list_jobs() -> list[dict]:
        return store.list_jobs()

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return job

    @app.delete("/jobs/{job_id}", status_code=204)
    def delete_job(job_id: str) -> None:
        job = store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job["status"] in ("queued", "processing"):
            raise HTTPException(
                status_code=409,
                detail="This analysis is still in progress. Wait for it to finish, then delete it.",
            )
        store.delete_job(job_id)
        shutil.rmtree(data_dir / "tmp" / job_id, ignore_errors=True)

    @app.delete("/analyses/{analysis_id}", status_code=204)
    def delete_analysis(analysis_id: str) -> None:
        if store.get_analysis(analysis_id) is None:
            raise HTTPException(status_code=404, detail="Analysis not found.")
        for job in store.list_jobs():
            if job["analysis_id"] == analysis_id:
                shutil.rmtree(data_dir / "tmp" / job["id"], ignore_errors=True)
        store.delete_analysis(analysis_id)

    @app.get("/analyses/{analysis_id}")
    def get_analysis(analysis_id: str) -> dict:
        analysis = store.get_analysis(analysis_id)
        if analysis is None:
            raise HTTPException(status_code=404, detail="Analysis not found.")
        return analysis

    def chat_analysis(analysis_id: str) -> dict:
        analysis = store.get_analysis(analysis_id)
        if analysis is not None:
            return analysis
        if store.get_job(analysis_id) is not None:
            raise HTTPException(
                status_code=409,
                detail="This analysis is not finished yet. Chat opens when it completes.",
            )
        raise HTTPException(status_code=404, detail="Analysis not found.")

    @app.get("/analyses/{analysis_id}/chat")
    def get_chat(analysis_id: str) -> list[dict]:
        chat_analysis(analysis_id)
        return store.list_chat_messages(analysis_id)

    @app.post("/analyses/{analysis_id}/chat")
    def ask_question(analysis_id: str, request: ChatRequest) -> dict:
        analysis = chat_analysis(analysis_id)
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=422, detail="Enter a question.")
        history = [(m["question"], m["answer"]) for m in store.list_chat_messages(analysis_id)]
        try:
            answer = answerer.answer(
                select_context(analysis["transcript"], question), history, question
            )
        except Exception as exc:
            logger.exception("Chat answer failed for analysis %s", analysis_id)
            raise HTTPException(
                status_code=502,
                detail=f"Could not get an answer: {str(exc) or type(exc).__name__}",
            )
        return store.add_chat_message(analysis_id, question, answer)

    return app

