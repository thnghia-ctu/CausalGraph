import csv
import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

from configs.config import BASE_DIR
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.normalization.factor_normalizer import FactorNormalizer


INPUT_PATH = BASE_DIR / "input" / "pattern_optimization_test_sentences.txt"
OUTPUT_PATH = BASE_DIR / "output" / "normalized_factors.csv"


def main() -> None:
    if "JAVA_HOME" not in os.environ and (java := shutil.which("java")):
        os.environ["JAVA_HOME"] = str(Path(java).resolve().parent.parent)

    extractor = RelationExtractor()
    normalizer = FactorNormalizer()
    rows = []
    factor_id = 0

    text = INPUT_PATH.read_text(encoding="utf-8-sig")
    for line in filter(str.strip, text.splitlines()):
        sentences = VnCoreNLPParser.parse_text(line.replace("_", " "))
        for extracted in extractor.extract_causal_relation(sentences):
            relation = extracted["re"]
            for factor in (relation.source, relation.target):
                if factor is None:
                    continue
                factor_id += 1
                for result in normalizer.normalize_factor(
                    factor,
                    extracted["sentence"],
                ):
                    rows.append({
                        "id": factor_id,
                        "original_text": result.original_text,
                        "normalized_text": result.normalized_text,
                        "concept_candidate": result.concept_candidate,
                        "state": (
                            json.dumps(asdict(result.state), ensure_ascii=False)
                            if result.state else ""
                        ),
                    })

    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "original_text",
                "normalized_text",
                "concept_candidate",
                "state",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Đã lưu {len(rows)} NormalizedFactor vào {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
