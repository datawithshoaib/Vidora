"""Streaming validation and storage of uploaded media.

The request body is parsed incrementally and written straight to disk, so the
size limit is enforced while streaming and a file is never held in memory.
"""

import shutil
from pathlib import Path

from fastapi import Request
from python_multipart.multipart import MultipartParser, parse_options_header

DEFAULT_MAX_UPLOAD_MB = 500

SUPPORTED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".flac", ".wma", ".weba",
    ".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm", ".mpeg", ".mpg", ".3gp",
}

UNSUPPORTED_MESSAGE = (
    "Unsupported file type. Upload an audio or video file such as MP3, WAV, M4A, MP4, MOV or WebM."
)


class UploadError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def too_large_message(limit: int) -> str:
    return f"File is too large. The maximum upload size is {limit / (1024 * 1024):g} MB."


def is_supported_media(filename: str, content_type: str) -> bool:
    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False
    content_type = content_type.split(";")[0].strip().lower()
    return content_type in ("", "application/octet-stream") or content_type.startswith(
        ("audio/", "video/")
    )


def upload_path(workdir: Path, filename: str) -> Path:
    return workdir / f"upload{Path(filename).suffix.lower()}"


class _Collector:
    """Parser callbacks that stream the `file` part to disk."""

    def __init__(self, workdir: Path, limit: int) -> None:
        self.workdir = workdir
        self.limit = limit
        self.filename: str | None = None
        self._field = b""
        self._value = b""
        self._headers: dict[bytes, bytes] = {}
        self._out = None
        self._written = 0
        self._current_is_file = False

    def callbacks(self) -> dict:
        return {
            "on_part_begin": self._part_begin,
            "on_header_field": self._header_field,
            "on_header_value": self._header_value,
            "on_header_end": self._header_end,
            "on_headers_finished": self._headers_finished,
            "on_part_data": self._part_data,
            "on_part_end": self.close,
        }

    def _part_begin(self) -> None:
        self._headers = {}
        self._field = self._value = b""
        self._current_is_file = False

    def _header_field(self, data: bytes, start: int, end: int) -> None:
        self._field += data[start:end]

    def _header_value(self, data: bytes, start: int, end: int) -> None:
        self._value += data[start:end]

    def _header_end(self) -> None:
        self._headers[self._field.lower()] = self._value
        self._field = self._value = b""

    def _headers_finished(self) -> None:
        _, params = parse_options_header(self._headers.get(b"content-disposition"))
        if params.get(b"name") != b"file" or b"filename" not in params or self.filename:
            return
        filename = params[b"filename"].decode("utf-8", "replace")
        content_type = self._headers.get(b"content-type", b"").decode("latin-1")
        if not is_supported_media(filename, content_type):
            raise UploadError(415, UNSUPPORTED_MESSAGE)
        self.filename = Path(filename.replace("\\", "/")).name
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._out = open(upload_path(self.workdir, filename), "wb")
        self._current_is_file = True

    def _part_data(self, data: bytes, start: int, end: int) -> None:
        if not self._current_is_file:
            return
        self._written += end - start
        if self._written > self.limit:
            raise UploadError(413, too_large_message(self.limit))
        self._out.write(data[start:end])

    def close(self) -> None:
        if self._out:
            self._out.close()
            self._out = None


async def receive_upload(request: Request, workdir: Path, limit: int) -> str:
    """Stream the multipart `file` field into workdir and return its filename.

    Raises UploadError and removes workdir if the upload is rejected or incomplete.
    """
    collector = _Collector(workdir, limit)
    try:
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit + 64 * 1024:
            raise UploadError(413, too_large_message(limit))
        content_type, params = parse_options_header(request.headers.get("content-type"))
        if content_type != b"multipart/form-data" or b"boundary" not in params:
            raise UploadError(422, "Send the media as a multipart form with a 'file' field.")
        parser = MultipartParser(params[b"boundary"], collector.callbacks())
        async for chunk in request.stream():
            parser.write(chunk)
        parser.finalize()
        if not collector.filename:
            raise UploadError(422, "No file was uploaded. Choose an audio or video file.")
        return collector.filename
    except Exception as exc:
        collector.close()
        shutil.rmtree(workdir, ignore_errors=True)
        if isinstance(exc, UploadError):
            raise
        raise UploadError(400, "The upload was incomplete or malformed. Try again.") from exc
    finally:
        collector.close()
