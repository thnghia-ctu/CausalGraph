import re
import unicodedata


_WHITESPACE_PATTERN = re.compile(r"\s+")
_LEADING_BULLET_PATTERN = re.compile(
    r"^\s*(?:(?:[-–—•▪◦*]+)|(?:\d+(?:\.\d+)*[.)]))\s+"
)
_TRAILING_SECTION_NUMBER_PATTERN = re.compile(
    r"\s+\d+(?:\.\d+)+\.?\s*$"
)


def normalize_surface(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("_", " ")
    normalized = normalized.casefold()
    return _WHITESPACE_PATTERN.sub(" ", normalized).strip()


def remove_noise_tokens(text: str) -> str:
    cleaned = _LEADING_BULLET_PATTERN.sub("", text)
    cleaned = _TRAILING_SECTION_NUMBER_PATTERN.sub("", cleaned)
    return _WHITESPACE_PATTERN.sub(" ", cleaned).strip()
