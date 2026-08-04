from src.data_models.dependency_token import DependencyToken, Sentence
from src.data_models.factor import Factor
from src.data_models.svo_triple import SVOTriple
from src.extraction.dependency_tree import DependencyTree

_OBJECT_ROLES = {"dob", "obj", "ccomp", "xcomp", "pob", "vmod", "coord", "mnr"}


class SVOExtractor:
    def extract(self, sentence: Sentence) -> SVOTriple | None:
        tree = DependencyTree(sentence)
        root = next((t for t in sentence.tokens if t.dep == "root"), None)
        if root is None:
            return None

        subject = tree.extract_source(root)
        obj = self._extract_object(tree, root)

        return SVOTriple(subject=subject, predicate=root.word, object=obj)

    def _extract_object(self, tree: DependencyTree, root: DependencyToken) -> Factor | None:
        targets = tree.find_dependents(root, roles=_OBJECT_ROLES)
        object_ids = {
            token_id
            for target in targets
            for token_id in tree.collect_subtree_ids(target)
            if token_id > root.id
        }
        object_ids = tree.strip_edge_punct(object_ids)
        if not object_ids:
            return None

        ordered = sorted(object_ids)
        return Factor(text=tree.surface_range(ordered[0], ordered[-1]), token_ids=ordered)
