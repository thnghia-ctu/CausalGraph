import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import LLM_RELATIONS_PATH, SPO_RELATIONS_PATH

COLUMNS = ["simple_sentence", "subject_text", "predicate", "object_text"]


def main():
    df = pd.read_csv(LLM_RELATIONS_PATH)[COLUMNS].fillna("")

    SPO_RELATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SPO_RELATIONS_PATH, index=False, encoding="utf-8-sig")

    print(f"Wrote {len(df)} rows -> {SPO_RELATIONS_PATH}")


if __name__ == "__main__":
    main()
