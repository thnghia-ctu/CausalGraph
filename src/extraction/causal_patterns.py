from src.data_models.trigger import Trigger
from src.data_models.dependency_token import DependencyToken
from src.extraction.dependency_tree import DependencyTree
from typing import Callable

PATTERN_HANDLERS: dict[str, Callable] = {}
PATTERN_MATCHERS: list[tuple[str, Callable]] = []


def register_pattern(name: str, matcher: Callable[[Trigger, DependencyTree], bool]):
    """
    Decorator đăng ký 1 structural pattern.
    matcher: hàm (trigger, tree) -> bool, kiểm tra điều kiện cấu trúc.
    Hàm được decorate chính là handler xử lý khi matcher trả True.
    """
    def decorator(handler_fn):
        PATTERN_HANDLERS[name] = handler_fn
        PATTERN_MATCHERS.append((name, matcher))
        return handler_fn
    return decorator


def classify_structure(trigger: Trigger, tree: DependencyTree) -> str:
    """Duyệt matcher theo thứ tự đăng ký, trả pattern đầu tiên khớp."""
    for name, matcher in PATTERN_MATCHERS:
        if matcher(trigger, tree):
            return name
    return "unmatched"

# --- Pattern A: direct_svo ---
# Cấu trúc: source + trigger (trực tiếp kết nối s vs t) + target.
def is_direct_svo(trigger: Trigger, tree: DependencyTree) -> bool:
    anchor = tree.find_trigger_head(trigger)
    if anchor is None:
        return False
    has_sub = len(tree.find_dependents(anchor, roles={"sub", "nsubj"})) > 0
    has_obj = len(
                tree.find_dependents(anchor, roles={"dob", "obj", "ccomp", "xcomp", "pob"})
                or tree.find_dependents(anchor, roles={"vmod"}, pos={"V", "A"})
                ) > 0
    return has_sub and has_obj

@register_pattern("direct_svo", is_direct_svo)
def handle_direct_svo(trigger: Trigger, tree: DependencyTree) -> dict:
    anchor = tree.find_trigger_head(trigger)
    source_tok = tree.find_dependents(anchor, roles={"sub", "nsubj"})[0]
    target_tok = tree.find_dependents(anchor, roles={"dob", "obj", "ccomp", "xcomp", "pob", "vmod"})[0]

    source_ids = tree.collect_subtree_ids(source_tok)
    target_ids = tree.collect_subtree_ids(target_tok)
    return {
        "pattern": "direct_svo",
        "source": tree.surface(source_ids),
        "target": tree.surface(target_ids),
    }

# --- Pattern B: vmod_chain ---
# Cấu trúc: source + head(V) + trigger dạng vmod/dep + cụm V/A (target).
def is_vmod_chain(trigger: Trigger, tree: DependencyTree) -> bool:
    anchor = tree.find_trigger_head(trigger)
    if anchor is None:
        return False
    head = tree.find_parent(anchor)
    if head is None or head.dep == "prp" or anchor.dep not in {"vmod", "dep"}:
        return False
    if head.pos not in {"V", "A"}:
        return False
    vp_children = tree.find_dependents(
        anchor, roles={"vmod", "dob", "ccomp", "xcomp"}, pos={"V", "A"}
    )
    return len(vp_children) > 0

@register_pattern("vmod_chain", is_vmod_chain)
def handle_vmod_chain(trigger: Trigger, tree: DependencyTree) -> dict:
    anchor = tree.find_trigger_head(trigger)
    head = tree.find_parent(anchor)
    vp_children = tree.find_dependents(
        anchor, roles={"vmod", "dob", "ccomp", "xcomp"}, pos={"V", "A"}
    )
    target_tok = vp_children[0]
    target_ids = set(tree.collect_subtree_ids(target_tok))         # FIX: set()

    trigger_branch_ids = set(tree.collect_subtree_ids(anchor))     # FIX: set()
    source_ids = set(tree.collect_subtree_ids(head)) - trigger_branch_ids  # FIX: set() cả 2 bên

    return {
        "pattern": "vmod_chain",
        "source": tree.surface(sorted(source_ids)),
        "target": tree.surface(sorted(target_ids)),
    }

# --- Pattern C: purpose_clause ---
# Cấu trúc: mệnh đề chính (source) + thành phần mục đích (nhằm, để, với_mục_đích) + trigger + target.
def is_purpose_clause(trigger: Trigger, tree: DependencyTree) -> bool:
    anchor = tree.find_trigger_head(trigger)
    if anchor is None:
        return False
    head = tree.find_parent(anchor)
    if head is None or head.dep != "prp" or anchor.dep not in {"vmod", "dep"}:
        return False
    return True

@register_pattern("purpose_clause", is_purpose_clause)
def handle_purpose_clause(trigger: Trigger, tree: DependencyTree) -> dict:
    anchor = tree.find_trigger_head(trigger)
    head = tree.find_parent(anchor)
    source_tok = tree.find_parent(head)
    targets = tree.find_dependents(anchor, roles={"dob", "obj", "ccomp", "xcomp", "pob", "vmod"})
   
    target_tok = targets[0] if targets else None

    source_ids = tree.collect_subtree_ids(source_tok, exclude=head)
    target_ids = tree.collect_subtree_ids(target_tok) if target_tok else []
    return {
        "pattern": "purpose_clause",
        "source": tree.surface(source_ids),
        "target": tree.surface(target_ids),
    }

# --- Pattern D: coord_conj ---
# Cấu trúc: source + cụm đẳng lập chứa trigger và các vế target.
def is_coord_conj(trigger: Trigger, tree: DependencyTree) -> bool:
    anchor = tree.find_trigger_head(trigger)
    head = tree.find_parent(anchor)
    if not (anchor.dep == "conj" or (head is not None and head.dep == "coord")):
        return False

    node = anchor
    while node.dep != "coord":
        parent = tree.find_parent(node)
        if parent is None:
            return False
        node = parent

    trigger_ids = trigger.token_ids()  # đây vốn đã là set, giữ nguyên
    conj_siblings = tree.find_dependents(node, roles={"conj"})
    real_targets = [
        s for s in conj_siblings
        if not (set(tree.collect_subtree_ids(s)) & trigger_ids)   # FIX: bọc set()
    ]
    return len(real_targets) > 0


@register_pattern("coord_conj", is_coord_conj)
def handle_coord_conj(trigger: Trigger, tree: DependencyTree) -> dict:
    anchor = tree.find_trigger_head(trigger)
    node = anchor
    while node.dep != "coord":
        node = tree.find_parent(node)
    coord_node = node

    trigger_ids = trigger.token_ids()
    conj_siblings = tree.find_dependents(coord_node, roles={"conj"})
    target_siblings = [
        s for s in conj_siblings
        if not (set(tree.collect_subtree_ids(s)) & trigger_ids)   # FIX
    ]

    target_ids = set()
    for sib in target_siblings:
        target_ids |= set(tree.collect_subtree_ids(sib))          # FIX: set(), dùng |=

    grandparent = tree.find_parent(coord_node)
    source_ids = set(tree.collect_subtree_ids(grandparent, exclude=coord_node)) if grandparent else set()  # FIX
    source_ids -= target_ids
    source_ids -= trigger_ids

    return {
        "pattern": "coord_conj",
        "source": tree.surface(sorted(source_ids)),
        "target": tree.surface(sorted(target_ids)),
    }


# --- Pattern fallback: unmatched ---
# Cấu trúc: không thuộc các dạng câu đã định nghĩa ở trên.
def handle_unmatched(trigger: Trigger, tree: DependencyTree) -> dict:
    return {
        "pattern": "unmatched",
        "source": None,
        "target": None,
        "note": "Không khớp pattern nào -> đẩy sang LLM fallback",
    }
