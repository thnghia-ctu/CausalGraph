import csv

from src.extraction.svo_extractor import SVOExtractor
from src.extraction.vncorenlp_parser import VnCoreNLPParser
from configs.config import BASE_DIR

PATH = BASE_DIR / "data" / "simplification" / "simplificated_sentences.csv"


def extract_svo(text: str, extractor: SVOExtractor) -> tuple[str, str, str]:
    sentences = VnCoreNLPParser.parse_text(text)
    if not sentences:
        return "", "", ""

    result = extractor.extract(sentences[0])
    if result is None:
        return "", "", ""

    subject = result.subject.text.replace("_", " ") if result.subject else ""
    predicate = result.predicate.replace("_", " ")
    obj = result.object.text.replace("_", " ") if result.object else ""
    return subject, predicate, obj


def main():
    with open(PATH, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    base_fieldnames = [name for name in fieldnames if name not in ("subject", "predicate", "object")]
    new_fieldnames = []
    for name in base_fieldnames:
        new_fieldnames.append(name)
        if name == "simple_sentence":
            new_fieldnames.extend(["subject", "predicate", "object"])

    extractor = SVOExtractor()
    total = len(rows)

    for i, row in enumerate(rows, start=1):
        try:
            subject, predicate, obj = extract_svo(row["simple_sentence"], extractor)
        except Exception as e:
            print(f"[{i}/{total}] error: {e}")
            subject, predicate, obj = "", "", ""

        row["subject"] = subject
        row["predicate"] = predicate
        row["object"] = obj

        if i % 200 == 0 or i == total:
            print(f"[{i}/{total}]")

    with open(PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done -> {PATH}")


if __name__ == "__main__":
    main()
