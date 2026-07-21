from collections import defaultdict

from src.data_models.relation import Relation
from src.data_models.dependency_token import DependencyToken, Sentence
from src.data_models.trigger import Trigger
from src.utils.helpers import  load_xlsx
from configs.config import BASE_DIR
from src.extraction.dependency_tree import DependencyTree
from src.extraction.causal_patterns import classify_structure, PATTERN_HANDLERS, handle_unmatched

class RelationExtractor:

    def __init__(self):
        df = load_xlsx(
            file_path=f"{BASE_DIR}/configs/causal_triggers.xlsx"
        )
        self.causal_triggers: dict[str, str] = {
            self._normalize(trigger): polarity
            for trigger, polarity in zip(df["trigger"], df["polarity"])
        }

        # Index theo TỪ ĐẦU TIÊN -> list các trigger (dạng list từ) bắt đầu bằng từ đó
        # VD: "tăng_cường" -> word_seq = ["tăng", "cường"] -> index["tăng"] += ["tăng","cường"]
        self.trigger_index: dict[str, list[str]] = defaultdict(list)
        for norm_trigger in self.causal_triggers.keys():
            word_seq = norm_trigger.split("_")
            self.trigger_index[word_seq[0]].append(norm_trigger)

        # Sắp xếp mỗi nhóm theo độ dài giảm dần -> ưu tiên match trigger dài trước
        for first_word in self.trigger_index:
            self.trigger_index[first_word].sort(key=len, reverse=True)

    @staticmethod
    def _normalize(text: str) -> str:
        return text.strip().replace(" ", "_").lower()

    def find_triggers(self, sentence: Sentence) -> list[Trigger]:
        tokens = sentence.tokens
        n_tokens = len(tokens)
        found: list[Trigger] = []
        used_ids: set[int] = set()

        for i in range(n_tokens):
            if tokens[i].id in used_ids:
                continue

            first_word = self._normalize(tokens[i].word).split("_")[0]
            candidates = self.trigger_index.get(first_word)
            if not candidates:
                continue  # từ đầu không khớp trigger nào -> bỏ qua ngay, không thử
            # candidates đã sort dài -> ngắn, nên match đầu tiên tìm được là dài nhất
            for word_seq in candidates:
                span_len = len(word_seq)
                j=i
                trig="_".join([self._normalize(tok.word) for tok in tokens[i:j+1]])
                while span_len<len(trig) and j<n_tokens-1:
                    j+=1
                    trig="_".join([self._normalize(tok.word) for tok in tokens[i:j+1]])
                if trig== word_seq:
                    found.append(Trigger(
                        start_id=tokens[i].id,
                        end_id=tokens[j].id,
                        text=word_seq
                    ))
                    used_ids.update(range(tokens[i].id, tokens[j].id + 1))
                    # break  # match xong trigger dài nhất -> bỏ qua các trigger ngắn hơn

        return sorted(found, key=lambda tr: tr.start_id)




        # triggers = []
        # all_words = list(self.causal_triggers.keys())
        # for word in all_words:
        #     word_tokens = word.split()
        #     n = len(word_tokens)
        #     for i in range(len(sentence.tokens) - n + 1):
        #         if all(sentence.tokens[i + j].word == word_tokens[j] for j in range(n)):
        #             triggers.append(Trigger(
        #                 start_id=sentence.tokens[i].id,
        #                 end_id=sentence.tokens[i + n - 1].id,
        #                 text=word
        #             ))

        # return triggers

    def extract_causal_relation(self, sentences: list[Sentence]) -> list[Relation]:
        relations = []
        for sentence in sentences:
            triggers = self.find_triggers(sentence)
            if triggers:
                for trigger in triggers:
                    tree = DependencyTree(sentence)
                    anchor = tree.find_trigger_head(trigger)
                    if anchor.pos not in {"V", "A"}:
                        continue
                    pattern_name = classify_structure(trigger, tree)
                    handler = PATTERN_HANDLERS.get(pattern_name, handle_unmatched)
                    result = handler(trigger, tree)
                    relations.append(
                        Relation(
                            source=result["source"],
                            trigger=trigger,
                            relationship=result["pattern"],
                            target=result["target"],
                            sentence=sentence
                        )
                    )

        return relations

    def test(self, sentences: list[Sentence]):
        re=[]
        for sentence in sentences:
            triggers = self.find_triggers(sentence)
            if triggers:
                tree=DependencyTree(sentence)
                root_word=next((token for token in sentence.tokens if token.dep=="root"), None)
                for trigger in triggers:
                    source_tokens=self.find_source(tree, tree.get_token(trigger.start_id))
                    source_text=" ".join(token.word for token in source_tokens) if source_tokens else None
                    target_tokens=self.find_target(tree, tree.get_token(trigger.end_id))
                    target_text=" ".join(token.word for token in target_tokens) if target_tokens else None
                    re.append({
                        "sen": " ".join(token.word for token in sentence.tokens),
                        "root": root_word.word if root_word else None,
                        "re": Relation(
                            source=source_text,
                            trigger=trigger,
                            relationship="unknown",
                            target=target_text
                        )
                    })
        return re

    def extract(
        self,
        sentences: list[Sentence]
    ):
        relations = []
        for sentence in sentences:
            root_word = next((token for token in sentence.tokens if token.dep == "root"), None)
            if not root_word:
                continue
            triggers = self.find_triggers(sentence, root_word.id)
            sources = self.find_span(sentence, root_word.id, {"sub" ,"nsubj", "advcl"})
            for trigger in triggers:                
                targets = self.find_span(sentence, trigger.end_id, {"obj", "dob", "pob", "ccomp", "xcomp"})
                source_text = self.expand_phrase(sources[0], sentence.tokens) if sources else None
                target_text = self.expand_phrase(targets[0], sentence.tokens) if targets else None
                relations.append(
                    {
                        "sen": " ".join(token.word for token in sentence.tokens),
                        "root": root_word.word,
                        "re": Relation(
                            source=source_text,
                            trigger=trigger,
                            relationship="unknown",
                            target=target_text
                        )
                    }
                )
        return relations

    def find_predicates(
        self,
        sentence: Sentence
    ) -> list[DependencyToken]:
        allowed_dep = {
            "root",
            "vmod",
            "coord",
            "conj"
        }

        return [
            token
            for token in sentence.tokens
            if (
                token.pos == "V"
                and token.dep in allowed_dep
            )
        ]
    

    
    def find_span(
        self,
        sentence: Sentence,
        predicate_id: int,
        roles: set
    ):
        candidates = []

        for token in sentence.tokens:
            if token.head == predicate_id:
                if token.dep in roles:
                    candidates.append(token)

        return None if not candidates else candidates
    
    def find_source(
    self,
    tree: DependencyTree,
    trigger: DependencyToken
    ) -> list[DependencyToken] | None:

        # Bước 1: tìm head
        heads = tree.find_dependents(trigger, {"sub", "nsubj"})

        if not heads:
            return None

        # Bước 2: mở rộng
        return tree.collect_subtree(heads[0])
    
    def find_target(
    self,
    tree: DependencyTree,
    trigger: DependencyToken
    ) -> list[DependencyToken] | None:

        heads = tree.find_dependents(trigger, {"dob", "obj", "xcomp", "ccomp", "pob"})

        if not heads:
            return None

        return tree.collect_subtree(heads[0])
        
    def expand_phrase(
        self,
        root,
        tokens
    ):

        EXPAND_DEPS = {
            "nmod",
            "amod",
            "det",

            "coord",
            "conj",

            "adv",

            "vmod",

            "dob",
            "iob",
            "pob"
        }

        phrase = []

        visited = set()

        def dfs(node):

            if node.id in visited:
                return

            visited.add(node.id)

            phrase.append(node)

            for child in tokens:

                if (
                    child.head == node.id
                    and child.dep in EXPAND_DEPS
                ):
                    dfs(child)

        dfs(root)

        phrase.sort(
            key=lambda x: x.id
        )

        return " ".join(
            token.word.replace("_", " ")
            for token in phrase
        )

    def find_subjects(
        self,
        predicate_id: int,
        sentence: Sentence
    ) -> list[DependencyToken]:

        ...

    def find_objects(
        self,
        predicate_id: int,
        sentence: Sentence
    ):

        ...

    def expand_noun_phrase(
        self,
        token: DependencyToken,
        sentence: Sentence
    ):

        ...
