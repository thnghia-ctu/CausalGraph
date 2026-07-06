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
def is_direct_svo(trigger: Trigger, tree: DependencyTree) -> bool:
    anchor = tree.find_trigger_head(trigger)
    has_sub = len(tree.find_dependents(anchor, roles={"sub", "nsubj"})) > 0
    has_obj = len(tree.find_dependents(anchor, roles={"dob", "obj", "ccomp", "xcomp", "pob"})) > 0
    return has_sub and has_obj

@register_pattern("direct_svo", is_direct_svo)
def handle_direct_svo(trigger: Trigger, tree: DependencyTree) -> dict:
    anchor = tree.find_trigger_head(trigger)
    source_tok = tree.find_dependents(anchor, roles={"sub", "nsubj"})[0]
    target_tok = tree.find_dependents(anchor, roles={"dob", "obj", "ccomp", "xcomp", "pob"})[0]

    source_ids = tree.collect_subtree_ids(source_tok)
    target_ids = tree.collect_subtree_ids(target_tok)
    return {
        "pattern": "direct_svo",
        "source": tree.surface(source_ids),
        "target": tree.surface(target_ids),
    }

# --- Pattern B: vmod_chain ---
def is_vmod_chain(trigger: Trigger, tree: DependencyTree) -> bool:
    anchor = tree.find_trigger_head(trigger)
    head = tree.find_parent(anchor)
    if head is None or anchor.dep not in {"vmod", "dep"}:
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

    source_ids = tree.collect_subtree_ids(head, exclude=anchor)
    target_ids = tree.collect_subtree_ids(target_tok)
    return {
        "pattern": "vmod_chain",
        "source": tree.surface(source_ids),
        "target": tree.surface(target_ids),
    }


# --- Pattern C: coord_conj ---
def is_coord_conj(trigger: Trigger, tree: DependencyTree) -> bool:
    anchor = tree.find_trigger_head(trigger)
    head = tree.find_parent(anchor)
    return anchor.dep == "conj" or (head is not None and head.dep == "coord")

@register_pattern("coord_conj", is_coord_conj)
def handle_coord_conj(trigger: Trigger, tree: DependencyTree) -> dict:
    anchor = tree.find_trigger_head(trigger)

    # Đi lên tìm node coord (từ nối "và"/"hoặc"), DỪNG LẠI đúng tại đó
    node = anchor
    while node.dep != "coord":
        parent = tree.find_parent(node)
        if parent is None:
            break
        node = parent
    coord_node = node if node.dep == "coord" else anchor  # fallback an toàn nếu không tìm thấy

    # SỬA: tìm "conj" ngay dưới coord_node, KHÔNG đi lên thêm 1 tầng nữa
    conj_siblings = tree.find_dependents(coord_node, roles={"conj"})

    target_ids = []
    for sib in conj_siblings:
        target_ids += tree.collect_subtree_ids(sib)

    # source = mọi thứ dưới cha của coord_node, TRỪ đi nhánh coord vừa lấy làm target
    grandparent = tree.find_parent(coord_node)
    if grandparent is not None:
        source_ids = tree.collect_subtree_ids(grandparent, exclude=coord_node)
    else:
        source_ids = []

    return {
        "pattern": "coord_conj",
        "source": tree.surface(source_ids),
        "target": tree.surface(target_ids),
    }


# --- Pattern fallback: unmatched ---
def handle_unmatched(trigger: Trigger, tree: DependencyTree) -> dict:
    return {
        "pattern": "unmatched",
        "source": None,
        "target": None,
        "note": "Không khớp pattern nào -> đẩy sang LLM fallback",
    }