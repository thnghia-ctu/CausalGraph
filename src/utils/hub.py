from pathlib import Path

from huggingface_hub import HfApi
from huggingface_hub import hf_hub_download


def resolve_hub_file(repo_id: str, filename: str, local_path: str | Path) -> Path:
    """Return a local artifact, downloading it to the HF cache when missing."""
    path = Path(local_path)
    if path.exists():
        return path
    return Path(hf_hub_download(repo_id=repo_id, filename=filename))


def push_file_to_hub(repo_id: str, path: str | Path) -> None:
    path = Path(path)
    api = HfApi()
    api.create_repo(repo_id, exist_ok=True)
    api.upload_file(path_or_fileobj=str(path), path_in_repo=path.name, repo_id=repo_id)
