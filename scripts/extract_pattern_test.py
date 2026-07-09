import csv
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.extraction.vncorenlp_parser import VnCoreNLPParser
from src.extraction.relation_extractor import RelationExtractor

INPUT_FILE = ROOT_DIR / "input" / "pattern_optimization_test_sentences.txt"
OUTPUT_FILE = ROOT_DIR / "output" / "pattern_test_relations.csv"
EVAL_FILE = ROOT_DIR / "output" / "pattern_test_eval.txt"


def read_sentences(path: Path) -> list[str]:
    return [s for s in (x.strip() for x in path.read_text(encoding="utf-8").splitlines()) if s]


def extract_rows(sentences: list[str]) -> tuple[list[dict], list[dict]]:
    extractor = RelationExtractor()
    rows, errors = [], []

    for line_id, text in enumerate(sentences, start=1):
        try:
            parsed_sentences = VnCoreNLPParser.parse_text(text)
            relations = extractor.extract_causal_relation(parsed_sentences)
        except Exception as exc:
            errors.append({"line_id": line_id, "sentence": text, "error": str(exc)})
            continue

        if not relations:
            rows.append({"line_id": line_id, "input_sentence": text, "parsed_sentence": "",
                         "pattern": "no_relation", "source": "", "trigger": "",
                         "target": "", "root": ""})
            continue

        for relation in relations:
            re = relation["re"]
            rows.append({
                "line_id": line_id,
                "input_sentence": text,
                "parsed_sentence": relation["sen"],
                "pattern": re.relationship,
                "source": re.source or "",
                "trigger": re.trigger.text,
                "target": re.target or "",
                "root": relation["root"] or "",
            })

    return rows, errors


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["line_id", "input_sentence", "parsed_sentence", "pattern",
              "source", "trigger", "target", "root"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_eval(path: Path, rows: list[dict], errors: list[dict]) -> None:
    patterns = Counter(row["pattern"] for row in rows)
    matched = [row for row in rows if row["pattern"] not in {"unmatched", "no_relation"}]
    lines = [f"total_output_rows: {len(rows)}", f"matched_rows: {len(matched)}",
             f"unmatched_rows: {patterns.get('unmatched', 0)}",
             f"no_relation_rows: {patterns.get('no_relation', 0)}",
             f"error_rows: {len(errors)}",
             f"matched_empty_source: {sum(not r['source'].strip() for r in matched)}",
             f"matched_empty_target: {sum(not r['target'].strip() for r in matched)}",
             "", "pattern_counts:"]
    lines += [f"- {name}: {count}" for name, count in patterns.most_common()]
    if errors:
        lines += ["", "errors:"]
        lines += [f"- line {e['line_id']}: {e['error']}" for e in errors]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sentences = read_sentences(INPUT_FILE)
    rows, errors = extract_rows(sentences)
    write_csv(OUTPUT_FILE, rows)
    write_eval(EVAL_FILE, rows, errors)
    print(f"Saved relations to {OUTPUT_FILE}")
    print(f"Saved evaluation to {EVAL_FILE}")
