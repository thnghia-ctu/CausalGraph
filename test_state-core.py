from pathlib import Path

import pandas as pd

from configs.config import BASE_DIR
from src.data_models.normalized_factor import NormalizedFactor
from src.extraction.relation_extractor import RelationExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.normalization.factor_normalizer import FactorNormalizer


def normalize_relation_factors(
    text: str,
) -> list[tuple[NormalizedFactor | None, NormalizedFactor | None]]:
    """Trả về các cặp NormalizedFactor của source và target trong text."""

    sentences = VnCoreNLPParser.parse_text(text.replace("_", " "))
    relations = RelationExtractor().extract_causal_relation(sentences)
    normalizer = FactorNormalizer()
    results = []

    for extracted in relations:
        source = extracted["re"].source
        target = extracted["re"].target
        if source is None and target is None:
            continue

        results.append(
            (
                normalizer.normalize(source.text) if source else None,
                normalizer.normalize(target.text) if target else None,
            )
        )

    return results


def factor_to_columns(
    prefix: str,
    factor: NormalizedFactor | None,
) -> dict[str, object]:
    state = factor.state if factor else None
    return {
        f"{prefix}_original_text": factor.original_text if factor else None,
        f"{prefix}_normalized_text": (
            factor.normalized_text if factor else None
        ),
        f"{prefix}_concept_candidate": (
            factor.concept_candidate if factor else None
        ),
        # f"{prefix}_concept_id": factor.concept_id if factor else None,
        # f"{prefix}_concept_label": factor.concept_label if factor else None,
        f"{prefix}_state_category": state.category if state else None,
        f"{prefix}_state_value": state.value if state else None,
        f"{prefix}_state_expression": state.expression if state else None,
        f"{prefix}_state_negated": state.negated if state else None,
        # f"{prefix}_confidence": factor.confidence if factor else None,
        # f"{prefix}_mapping_method": (
        #     factor.mapping_method if factor else None
        # ),
        # f"{prefix}_needs_review": factor.needs_review if factor else None,
    }


def save_results_to_csv(
    results: list[
        tuple[NormalizedFactor | None, NormalizedFactor | None]
    ],
    output_path: str | Path,
) -> None:
    rows = [
        {
            **factor_to_columns("source", source),
            **factor_to_columns("target", target),
        }
        for source, target in results
    ]

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    input_path = BASE_DIR / "input" / "pattern_optimization_test_sentences.txt"
    output_path = BASE_DIR / "output" / "test-state-core.csv"
    text = input_path.read_text(encoding="utf-8-sig")
    results = normalize_relation_factors(text)
    save_results_to_csv(results, output_path)
    print(f"Đã lưu {len(results)} kết quả vào {output_path}")
