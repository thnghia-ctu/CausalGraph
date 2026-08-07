from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from charset_normalizer import from_bytes

from src.data_models.document import Document

UPLOAD_SOURCE_TYPE = "upload"


@dataclass
class UploadResult:
    documents: list[Document] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


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


def save_uploaded_documents(files, dataset_dir: str | Path) -> UploadResult:
    dataset_dir = Path(dataset_dir)
    raw_dir = dataset_dir / "raw" / UPLOAD_SOURCE_TYPE
    raw_dir.mkdir(parents=True, exist_ok=True)
    index_path = dataset_dir / "raw" / "documents.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    result = UploadResult()
    with open(index_path, "a", encoding="utf-8") as index_file:
        for file in files:
            text = _decode(file.getvalue())
            if text is None:
                result.skipped_files.append(file.name)
                continue

            text = text.strip()
            if not text:
                continue

            doc_id = hashlib.sha1(f"{file.name}:{text}".encode("utf-8")).hexdigest()[:12]
            filename = f"{doc_id}_text.txt"
            (raw_dir / filename).write_text(text, encoding="utf-8")

            document = Document(doc_id=doc_id, url="", path=filename, source_type=UPLOAD_SOURCE_TYPE)
            result.documents.append(document)
            index_file.write(json.dumps(asdict(document), ensure_ascii=False) + "\n")

    return result
