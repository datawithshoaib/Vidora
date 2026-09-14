from utils.audio_processor import process_input
from core.transcriber import transcribe_all

source = "https://www.youtube.com/watch?v=v4F1gFy-hqg&t=156s"

chunks = process_input(source)
transcript = transcribe_all(chunks, translate=False)

print(transcript)
