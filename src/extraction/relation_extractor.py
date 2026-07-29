from src.causal_detection.trigger_classifier import TriggerCausalClassifier
from src.data_models.relation import Relation
from src.data_models.dependency_token import DependencyToken, Sentence
from src.extraction.dependency_tree import DependencyTree
from src.extraction.causal_patterns import classify_structure, PATTERN_HANDLERS, handle_unmatched

class RelationExtractor:

    def __init__(self):
        self.trigger_classifier = TriggerCausalClassifier()

    def extract_causal_relation(self, sentences: list[Sentence]) -> list[Relation]:
        relations = []
        for sentence in sentences:
            triggers = self.trigger_classifier.find_triggers(sentence)
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
            triggers = self.trigger_classifier.find_triggers(sentence)
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
            triggers = self.trigger_classifier.find_triggers(sentence)
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
