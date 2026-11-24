from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.pipeline import Notes


class ManualRunner:
    """Holds submitted work until the test decides to run it."""

    def __init__(self) -> None:
        self.pending: list = []

    def submit(self, fn) -> None:
        self.pending.append(fn)

    def run_all(self) -> None:
        while self.pending:
            self.pending.pop(0)()


class FakeFetcher:
    def __init__(self) -> None:
        self.urls: list[str] = []
        self.workdirs: list[Path] = []
        self.error: Exception | None = None
        self.on_call = None

    def fetch(self, url: str, workdir: Path) -> list[Path]:
        self.urls.append(url)
        self.workdirs.append(workdir)
        if self.on_call:
            self.on_call()
        chunk = workdir / "chunk_0.wav"
        chunk.write_bytes(b"audio")
        if self.error:
            raise self.error
        return [chunk]


class FakeTranscriber:
    def __init__(self) -> None:
        self.calls: list[list[Path]] = []
        self.on_call = None

    def transcribe(self, chunks: list[Path]) -> str:
        self.calls.append(chunks)
        if self.on_call:
            self.on_call()
        return "hello from the video"


class FakeAnalyzer:
    def __init__(self) -> None:
        self.transcripts: list[str] = []
        self.error: Exception | None = None

    def analyze(self, transcript: str) -> Notes:
        self.transcripts.append(transcript)
        if self.error:
            raise self.error
        return Notes(
            title="A Fake Title",
            summary="- a summary",
            action_items="1. do a thing",
            key_decisions="1. decided a thing",
            open_questions="1. why?",
        )


class Env:
    def __init__(self, tmp_path: Path) -> None:
        self.data_dir = tmp_path / "data"
        self.runner = ManualRunner()
        self.fetcher = FakeFetcher()
        self.transcriber = FakeTranscriber()
        self.analyzer = FakeAnalyzer()
        self.app = create_app(
            data_dir=self.data_dir,
            fetcher=self.fetcher,
            transcriber=self.transcriber,
            analyzer=self.analyzer,
            runner=self.runner,
        )
        self.client = TestClient(self.app)

    def submit(self, url: str = "https://www.youtube.com/watch?v=abc123XYZ_-"):
        return self.client.post("/jobs", json={"url": url})

    def restart(self) -> TestClient:
        """A new app instance over the same data directory."""
        return TestClient(create_app(data_dir=self.data_dir, runner=self.runner))


@pytest.fixture
def env(tmp_path: Path) -> Env:
    return Env(tmp_path)
