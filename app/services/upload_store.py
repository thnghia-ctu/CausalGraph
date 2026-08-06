from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from src.data_models.document import Document

UPLOAD_SOURCE_TYPE = "upload"


def save_uploaded_documents(files, dataset_dir: str | Path) -> list[Document]:
    dataset_dir = Path(dataset_dir)
    raw_dir = dataset_dir / "raw" / UPLOAD_SOURCE_TYPE
    raw_dir.mkdir(parents=True, exist_ok=True)
    index_path = dataset_dir / "raw" / "documents.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    documents: list[Document] = []
    with open(index_path, "a", encoding="utf-8") as index_file:
        for file in files:
            text = file.getvalue().decode("utf-8", errors="ignore").strip()
            if not text:
                continue

            doc_id = hashlib.sha1(f"{file.name}:{text}".encode("utf-8")).hexdigest()[:12]
            filename = f"{doc_id}_text.txt"
            (raw_dir / filename).write_text(text, encoding="utf-8")

            document = Document(doc_id=doc_id, url="", path=filename, source_type=UPLOAD_SOURCE_TYPE)
            documents.append(document)
            index_file.write(json.dumps(asdict(document), ensure_ascii=False) + "\n")

    return documents
