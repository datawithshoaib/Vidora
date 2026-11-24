"""Pick the transcript passages that matter for a question.

Short transcripts go to the model whole. Longer ones are cut into overlapping
word windows and ranked by how many (rarer-weighted) question words they share,
then the best few are returned in transcript order. No embeddings or vector
index: nothing extra to store, rebuild or delete with an analysis.
"""

import math
import re

FULL_CONTEXT_CHARS = 12000
WINDOW_WORDS = 220
STEP_WORDS = 180
MAX_WINDOWS = 6

_STOPWORDS = frozenset(
    "a an and are as at be but by did do does for from had has have he her his how i in is it "
    "its me of on or our she so that the their them they this to us was we were what when "
    "where which who why will with would you your about said say".split()
)


def _terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in _STOPWORDS}


def select_context(transcript: str, question: str) -> str:
    if len(transcript) <= FULL_CONTEXT_CHARS:
        return transcript
    words = transcript.split()
    windows = [
        words[start : start + WINDOW_WORDS] for start in range(0, len(words), STEP_WORDS)
    ]
    window_terms = [_terms(" ".join(w)) for w in windows]
    query = _terms(question)
    weight = {
        t: math.log(1 + len(windows) / (1 + sum(t in wt for wt in window_terms))) for t in query
    }
    scores = [sum(weight[t] for t in query & wt) for wt in window_terms]
    best = sorted(range(len(windows)), key=lambda i: (-scores[i], i))[:MAX_WINDOWS]
    return "\n\n[...]\n\n".join(" ".join(windows[i]) for i in sorted(best))
