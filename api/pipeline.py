"""Analysis pipeline orchestration.

The external steps (download, transcription, AI notes) are protocols so the
service can be wired with real adapters in production and fakes in tests.
"""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from api.store import Store
from api.uploads import upload_path

logger = logging.getLogger("vidora.pipeline")


@dataclass(frozen=True)
class Notes:
    title: str
    summary: str
    action_items: str
    key_decisions: str
    open_questions: str


class MediaFetcher(Protocol):
    def fetch(self, url: str, workdir: Path) -> list[Path]:
        """Download the source and return audio chunk files inside workdir."""


class UploadPreparer(Protocol):
    def prepare(self, path: Path, workdir: Path) -> list[Path]:
        """Convert an uploaded audio/video file into audio chunk files inside workdir."""


class Transcriber(Protocol):
    def transcribe(self, chunks: list[Path]) -> str:
        """Return the English transcript of the audio chunks."""


class Analyzer(Protocol):
    def analyze(self, transcript: str) -> Notes:
        """Generate title, summary and extracted lists from a transcript."""


class Answerer(Protocol):
    def answer(self, context: str, history: list[tuple[str, str]], question: str) -> str:
        """Answer a question from transcript context and earlier (question, answer) turns."""


class Runner(Protocol):
    def submit(self, fn) -> None:
        """Run fn in the background."""


class Pipeline:
    def __init__(
        self,
        store: Store,
        tmp_root: Path,
        fetcher: MediaFetcher,
        transcriber: Transcriber,
        analyzer: Analyzer,
        preparer: UploadPreparer,
    ) -> None:
        self.preparer = preparer
        self.store = store
        self.tmp_root = tmp_root
        self.fetcher = fetcher
        self.transcriber = transcriber
        self.analyzer = analyzer

    def run(self, job_id: str) -> None:
        """Process one job. Never raises: failures are recorded on the job."""
        workdir = self.tmp_root / job_id
        try:
            job = self.store.get_job(job_id)
            workdir.mkdir(parents=True, exist_ok=True)

            if job["source_kind"] == "upload":
                self.store.update_job(job_id, status="processing", step="preparing")
                chunks = self.preparer.prepare(upload_path(workdir, job["source"]), workdir)
            else:
                self.store.update_job(job_id, status="processing", step="downloading")
                chunks = self.fetcher.fetch(job["source"], workdir)

            self.store.update_job(job_id, step="transcribing")
            transcript = self.transcriber.transcribe(chunks)

            self.store.update_job(job_id, step="analyzing")
            notes = self.analyzer.analyze(transcript)

            analysis = self.store.create_analysis(
                transcript=transcript,
                title=notes.title,
                summary=notes.summary,
                action_items=notes.action_items,
                key_decisions=notes.key_decisions,
                open_questions=notes.open_questions,
            )
            self.store.update_job(
                job_id, status="completed", step=None, analysis_id=analysis["id"]
            )
        except Exception as exc:
            logger.exception("Job %s failed", job_id)
            self.store.update_job(
                job_id, status="failed", step=None, error=str(exc) or type(exc).__name__
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
