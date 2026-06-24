from src.data_models.relation import Relation
from src.data_models.dependency_token import DependencyToken, Sentence
from src.data_models.trigger import Trigger

class RelationExtractor:

    def __init__(self):
        self.causal_triggers = {
            "facilitator": [          # thúc đẩy
                "giúp", "cho phép", "tạo điều kiện", "thúc đẩy",
                "nâng cao", "cải thiện", "tăng cường", "nhờ", "vì vậy"
            ],
            "barrier": [              # kìm hãm
                "cản trở", "hạn chế", "gây khó khăn", "làm chậm",
                "tuy nhiên", "nhưng", "mặc dù", "thiếu", "làm cho...khó"
            ],
            "neutral_causal": [       # nhân-quả trung tính
                "dẫn đến", "do", "bởi vì", "kết quả là",
                "vì", "khiến", "làm cho", "do đó"
            ]
        }

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
    
    def find_triggers(self, sentence, root_id):

        triggers = []
        all_words = []

        for words in self.causal_triggers.values():
            all_words.extend(words)

        for word in all_words:
            word_tokens = word.split()
            n = len(word_tokens)
            for i in range(len(sentence.tokens) - n + 1):
                if all(sentence.tokens[i + j].word == word_tokens[j] for j in range(n)) and sentence.tokens[i].head == root_id:
                    triggers.append(Trigger(
                        start_id=sentence.tokens[i].id,
                        end_id=sentence.tokens[i + n - 1].id,
                        text=word
                    ))

        return triggers
    
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