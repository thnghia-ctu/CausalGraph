# Thử nghiệm với một script để import từ điển từ file txt vào json. 
# Mỗi dòng trong file txt sẽ là một term mới, nếu term đó chưa tồn tại trong lexicon thì sẽ được thêm vào.

from src.utils.lexicon_manager import LexiconManager

TXT_PATH = "configs/lexicon.txt"
JSON_PATH = "configs/lexicon.json"


def load_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def main():

    lex = LexiconManager(JSON_PATH)
    terms = load_txt(TXT_PATH)

    added, skipped = 0, 0

    for line in terms:

        if "|" in line:
            term, weight = line.split("|", 1)
            weight = float(weight.strip())
        else:
            term = line
            weight = 1.0

        is_added = lex.add_term(term, weight)

        if is_added:
            added += 1
        else:
            skipped += 1

    print(f"Added {added} new terms")
    print(f"Skipped {skipped} existing terms")


if __name__ == "__main__":
    main()