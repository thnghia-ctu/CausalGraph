from pathlib import Path

import py_vncorenlp

from configs.config import BASE_DIR


VNCORENLP_DIR = BASE_DIR / "resources" / "third_party" / "vncorenlp"


def model_is_downloaded(model_dir: Path) -> bool:
    """Return whether the VnCoreNLP JAR and model directory are present."""
    return (model_dir / "VnCoreNLP-1.2.jar").is_file() and (
        model_dir / "models"
    ).is_dir()


def main() -> None:
    if model_is_downloaded(VNCORENLP_DIR):
        print(f"VnCoreNLP is already available at: {VNCORENLP_DIR}")
        return

    if VNCORENLP_DIR.exists():
        raise RuntimeError(
            f"Incomplete VnCoreNLP directory found at: {VNCORENLP_DIR}. "
            "Remove or rename it before downloading again."
        )

    # py_vncorenlp creates the ``models`` subdirectory itself, but expects its
    # parent (``save_dir``) to already exist.
    VNCORENLP_DIR.mkdir(parents=True, exist_ok=False)

    print(f"Downloading VnCoreNLP to: {VNCORENLP_DIR}")
    py_vncorenlp.download_model(save_dir=str(VNCORENLP_DIR))
    print("VnCoreNLP download completed.")


if __name__ == "__main__":
    main()
