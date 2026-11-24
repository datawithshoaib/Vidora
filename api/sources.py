"""Source validation."""

from urllib.parse import parse_qs, urlparse

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
SHORT_HOST = "youtu.be"

INVALID_URL_MESSAGE = (
    "Enter a valid YouTube video link, for example https://www.youtube.com/watch?v=..."
)


def is_youtube_video_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    segments = [s for s in parsed.path.split("/") if s]
    if host == SHORT_HOST:
        return len(segments) == 1
    if host in YOUTUBE_HOSTS:
        if parsed.path == "/watch":
            return bool(parse_qs(parsed.query).get("v", [""])[0])
        return len(segments) == 2 and segments[0] in ("shorts", "embed", "live")
    return False
