"""Text helpers shared by the tools."""
import re

_QUOTES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def normalise(text: str) -> str:
    """Lower-case, unify curly quotes, drop punctuation and squash spaces, so quote checks ignore formatting."""
    text = (text or "").translate(_QUOTES).lower()
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
