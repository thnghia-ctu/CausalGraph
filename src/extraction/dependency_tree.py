from src.data_models.factor import Factor
from src.data_models.trigger import Trigger
from src.data_models.dependency_token import  Sentence, DependencyToken
from collections import defaultdict

class DependencyTree:
    def __init__(self, sentence: Sentence):
        self.sentence = sentence
        self.children_map = self._build_children_map()
        self.token_map = {
            token.id: token
            for token in sentence.tokens
        }

    def _build_children_map(self)-> dict[int, list[DependencyToken]]:
        children_map = defaultdict(list)
        for token in self.sentence.tokens:
            children_map[token.head].append(token)
        return children_map
    
    def get_token(self, token_id: int)-> DependencyToken | None:
        return self.token_map.get(token_id, None)
    
    # Trigger có thể là nhiều token, nên cần tìm head của trigger (token có head không thuộc trigger)
    def find_trigger_head(self, trigger: Trigger) -> DependencyToken | None:
        trigger_ids = trigger.token_ids()
        candidates = [
            self.token_map[tok_id] for tok_id in trigger_ids if tok_id in self.token_map
        ]
        for token in candidates:
            if token.head is not None and token.head not in trigger_ids:
                return token
        return candidates[0] if candidates else None

    def find_parent(self, token: DependencyToken) -> DependencyToken | None:        
        if token.head == 0:
            return None
        return self.token_map.get(token.head)
    
    def find_children(self, token: DependencyToken) -> list[DependencyToken]:
        return self.children_map.get(token.id, [])
    
    def find_dependents(
        self,
        token: DependencyToken,
        roles: set[str],
        pos: set[str] | None = None,
        excepted_pos: set[str] | None = None,
    ) -> list[DependencyToken]:
        children = []
        for child in self.find_children(token):
            if child.dep in roles:
                if pos is not None and child.pos not in pos:
                    continue
                if excepted_pos is not None and child.pos in excepted_pos:
                    continue
                if child.dep in {"coord"} and child.word not in {"và"}:
                    continue

                children.append(child)
        return children

    def collect_subtree(
        self,
        token: DependencyToken
    ) -> list[DependencyToken]:
        subtree = []
        def dfs(node: DependencyToken):
            subtree.append(node)
            for child in self.find_children(node):
                dfs(child)
        dfs(token)
        return sorted(subtree, key=lambda t: t.id)
    
    def collect_subtree_ids(
        self,
        token: DependencyToken,
        exclude: DependencyToken | None = None,
    ) -> list[int]:
        """
        Giống collect_subtree nhưng trả về id, có thể loại trừ 1 nhánh con
        (VD: lấy subtree của head trigger nhưng bỏ nhánh trigger ra)
        """
        exclude_ids = set()
        if exclude is not None:
            exclude_ids = self.collect_subtree_ids(exclude)

        subtree = []
        def dfs(node: DependencyToken):
            if node.id in exclude_ids or node.dep in {"prp", "mnr"}:
                return
            subtree.append(node)
            for child in self.find_children(node):
                dfs(child)
        dfs(token)
        return sorted(t.id for t in subtree)

    def surface(self, ids: list[int], skip_punct: bool = False) -> str:
        """Ghép các token id lại thành câu theo đúng thứ tự."""
        words = []
        for i in sorted(ids):
            tok = self.token_map[i]
            if skip_punct and tok.pos == "CH":
                continue
            words.append(tok.word)
        return " ".join(words)

    def surface_range(
        self,
        start_id: int,
        end_id: int,
        skip_punct: bool = False,
    ) -> str:
        """Ghép các token trong khoảng ID đóng ``[start_id, end_id]``."""
        if start_id > end_id:
            raise ValueError("start_id must be less than or equal to end_id")

        return self.surface(list(range(start_id, end_id + 1)), skip_punct)

    def extract_source(
        self,
        anchor: DependencyToken | None,
    ) -> Factor | None:
        """Trích xuất các token source có ID nhỏ hơn ID của anchor."""
        if anchor is None:
            return None

        sources = self.find_dependents(anchor, roles={"sub", "nsubj"})
        source_ids = {
            token_id
            for source in sources
            for token_id in self.collect_subtree_ids(source)
            if token_id < anchor.id
        }        

        return Factor(text=self.surface_range(min(source_ids), max(source_ids)), token_ids=list(sorted(source_ids))) if source_ids else None

    def extract_target(
        self,
        anchor: DependencyToken | None,
    ) -> Factor | None:
        """Trích xuất các token target có ID lớn hơn ID của anchor."""
        if anchor is None:
            return None

        targets = self.find_dependents(
            anchor,
            roles={"dob", "obj", "ccomp", "xcomp", "pob", "vmod", "coord"},
            excepted_pos={"C", "E", "R", "T", "X"},
        )
        target_ids = {
            token_id
            for target in targets
            for token_id in self.collect_subtree_ids(target)
            if token_id > anchor.id
        }

        return Factor(text=self.surface_range(min(target_ids), max(target_ids)), token_ids=list(sorted(target_ids))) if target_ids else None

    def strip_edge_punct(self, ids: set[int] | list[int]) -> set[int]:
        """Bỏ token dấu câu ở đầu/cuối cụm, giữ dấu câu bên trong.
        Cần cho vmod_chain: subtree của head luôn kéo theo 'punct' treo vào root.
        """
        ordered = sorted(ids)
        start, end = 0, len(ordered) - 1
        while start <= end and self.token_map[ordered[start]].pos == "CH":
            start += 1
        while end >= start and self.token_map[ordered[end]].pos == "CH":
            end -= 1
        return set(ordered[start:end + 1])