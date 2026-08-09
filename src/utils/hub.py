from pathlib import Path

from huggingface_hub import HfApi


def push_file_to_hub(repo_id: str, path: str | Path) -> None:
    path = Path(path)
    api = HfApi()
    api.create_repo(repo_id, exist_ok=True)
    api.upload_file(path_or_fileobj=str(path), path_in_repo=path.name, repo_id=repo_id)
