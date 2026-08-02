import pandas as pd

from src.causal_detection.trigger_classifier import TriggerCausalClassifier

REQUIRED_CONCEPT_COLUMNS = ("source_concept_candidate", "target_concept_candidate")

_trigger_classifier = TriggerCausalClassifier()


def drop_missing_concept(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing = df[list(REQUIRED_CONCEPT_COLUMNS)].isna().any(axis=1)
    rejected = df[missing].assign(reject_reason="missing_concept_candidate")
    return df[~missing], rejected


def drop_non_causal_simple_sentence(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    is_causal = df["simple_sentence"].fillna("").apply(_trigger_classifier.is_causal_text)
    rejected = df[~is_causal].assign(reject_reason="non_causal_simple_sentence")
    return df[is_causal], rejected


RELATION_FILTERS = (drop_missing_concept, drop_non_causal_simple_sentence)


def filter_relations(
    df: pd.DataFrame,
    filters: tuple = RELATION_FILTERS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    kept = df
    rejected_parts = []
    for relation_filter in filters:
        kept, rejected = relation_filter(kept)
        rejected_parts.append(rejected)
    rejected_all = (
        pd.concat(rejected_parts, ignore_index=True) if rejected_parts else df.iloc[:0]
    )
    return kept, rejected_all
