from __future__ import annotations

from dataclasses import dataclass, field

from charset_normalizer import from_bytes

@dataclass
class UrlListResult:
    urls: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


def _decode(raw_bytes: bytes) -> str | None:
    match = from_bytes(raw_bytes).best()
    return None if match is None else str(match)


def parse_url_list_files(files) -> UrlListResult:
    result = UrlListResult()
    for file in files:
        text = _decode(file.getvalue())
        if text is None:
            result.skipped_files.append(file.name)
            continue
        result.urls.extend(line.strip() for line in text.splitlines() if line.strip())
    return result
