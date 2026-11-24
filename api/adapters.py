"""Production adapters for the pipeline protocols.

Heavy dependencies (yt-dlp, pydub, Whisper, LangChain) are imported lazily so
the API starts quickly and tests never load them.
"""

import os
from pathlib import Path

from api.pipeline import Notes

CHUNK_MINUTES = 10


class YoutubeFetcher:
    """Download a YouTube video's audio with yt-dlp and split it into WAV chunks."""

    def fetch(self, url: str, workdir: Path) -> list[Path]:
        import yt_dlp
        from pydub import AudioSegment

        options = {
            "format": "bestaudio/best",
            "outtmpl": str(workdir / "source.%(ext)s"),
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "192"}
            ],
            "noplaylist": True,
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.extract_info(url, download=True)

        wav_path = workdir / "source.wav"
        audio = AudioSegment.from_wav(wav_path).set_channels(1).set_frame_rate(16000)
        chunk_ms = CHUNK_MINUTES * 60 * 1000
        chunks = []
        for index, start in enumerate(range(0, len(audio), chunk_ms)):
            chunk_path = workdir / f"chunk_{index}.wav"
            audio[start : start + chunk_ms].export(chunk_path, format="wav")
            chunks.append(chunk_path)
        wav_path.unlink(missing_ok=True)
        return chunks


class WhisperTranscriber:
    """Local Whisper transcription. English only."""

    def __init__(self, model_name: str | None = None, model=None) -> None:
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "small")
        self._model = model

    def _load(self):
        if self._model is None:
            import whisper

            self._model = whisper.load_model(self.model_name)
        return self._model

    def transcribe(self, chunks: list[Path]) -> str:
        model = self._load()
        parts = [
            model.transcribe(str(chunk), task="transcribe", language="en")["text"].strip()
            for chunk in chunks
        ]
        return " ".join(part for part in parts if part)


class MistralAnalyzer:
    """Title, summary and extracted lists generated with Mistral through LangChain."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")

    def _llm(self, temperature: float):
        from langchain_mistralai import ChatMistralAI

        if not self.api_key:
            raise RuntimeError("MISTRAL_API_KEY is not set. Add it to your .env file.")
        return ChatMistralAI(
            model_name="mistral-small-latest",
            mistral_api_key=self.api_key,
            temperature=temperature,
        )

    def _ask(self, system: str, text: str, temperature: float = 0.2) -> str:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages([("system", system), ("human", "{text}")])
        return (prompt | self._llm(temperature) | StrOutputParser()).invoke({"text": text})

    def _summarize(self, transcript: str) -> str:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=200)
        partials = [
            self._ask("Summarize this portion of a video transcript concisely.", chunk, 0.3)
            for chunk in splitter.split_text(transcript)
        ]
        return self._ask(
            "You are an expert summarizer. Combine these partial summaries into one "
            "final professional summary in bullet points.",
            "\n\n".join(partials),
            0.3,
        )

    def analyze(self, transcript: str) -> Notes:
        title = self._ask(
            "Based on the transcript, generate a short professional title (max 8 words). "
            "Only return the title, nothing else.",
            transcript[:2000],
            0.3,
        ).strip().strip('"')
        return Notes(
            title=title,
            summary=self._summarize(transcript),
            action_items=self._ask(
                "You are an expert analyst. From the transcript, extract all action items. "
                "For each provide the task, the owner (who is responsible) and the deadline "
                "(if mentioned, else 'Not specified'). Format as a numbered list. "
                "If none found say 'No action items found.'",
                transcript,
            ),
            key_decisions=self._ask(
                "You are an expert analyst. From the transcript, extract all key decisions "
                "made. Format as a numbered list. If none found say 'No key decisions found.'",
                transcript,
            ),
            open_questions=self._ask(
                "From the transcript, extract all unresolved questions or topics needing "
                "follow-up. Format as a numbered list. If none found say 'No open questions found.'",
                transcript,
            ),
        )
