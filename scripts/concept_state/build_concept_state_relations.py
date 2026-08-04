import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from configs.config import CONCEPT_STATE_RELATIONS_PATH, LLM_RELATIONS_PATH

COLUMNS = ["factor_text", "concept_candidate", "state"]


def main():
    df = pd.read_csv(LLM_RELATIONS_PATH).fillna("")

    source = df.rename(columns={
        "subject_text": "factor_text",
        "source_concept_candidate": "concept_candidate",
        "source_state": "state",
    })[COLUMNS]
    target = df.rename(columns={
        "object_text": "factor_text",
        "target_concept_candidate": "concept_candidate",
        "target_state": "state",
    })[COLUMNS]

    combined = pd.concat([source, target], ignore_index=True)
    combined = combined[combined["factor_text"].str.strip() != ""]

    CONCEPT_STATE_RELATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(CONCEPT_STATE_RELATIONS_PATH, index=False, encoding="utf-8-sig")

    print(f"Wrote {len(combined)} rows -> {CONCEPT_STATE_RELATIONS_PATH}")


if __name__ == "__main__":
    main()
