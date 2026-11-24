from pathlib import Path

from api.adapters import WhisperTranscriber


class RecordingModel:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def transcribe(self, path: str, **options) -> dict:
        self.calls.append(options)
        return {"text": f" text of {Path(path).name} "}


def test_transcription_is_english_only_and_joins_chunks() -> None:
    model = RecordingModel()

    text = WhisperTranscriber(model=model).transcribe([Path("a.wav"), Path("b.wav")])

    assert text == "text of a.wav text of b.wav"
    assert all(call["language"] == "en" for call in model.calls)
