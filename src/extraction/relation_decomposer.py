"""Decompose extracted causal relations into atomic relations.

Chiến lược tách:
    1. Comma-verb: tách tại dấu phẩy khi ngay sau là vị ngữ mới (V),
       xử lý liệt kê mệnh đề "VP₁, VP₂, VP₃".
    2. Coord/conj: tách dựa trên quan hệ coord/conj trong dependency tree,
       xử lý liên kết "A và B" ở mọi cấp (danh từ, động từ, mệnh đề).
    3. Đệ quy: mỗi phần con được kiểm tra tiếp để xử lý "VP₁, VP₂ và VP₃".
"""

from __future__ import annotations

from src.data_models.dependency_token import DependencyToken
from src.data_models.factor import Factor
from src.data_models.relation import Relation
from src.extraction.dependency_tree import DependencyTree


class RelationDecomposer:
    """Split coordinated / enumerated factors into atomic ones."""

    _SEPARATORS = {",", "và", "hoặc"}

    # Số token không thuộc conjunct nào được phép tồn tại khi dùng
    # coord/conj split.  Nếu vượt quá, coordination bị nhúng quá sâu
    # trong factor → không tách.
    _MAX_UNACCOUNTED = 2

    def __init__(self, tree: DependencyTree) -> None:
        self.tree = tree

    # ── public API ──────────────────────────────────────────────

    def decompose(self, relation: Relation) -> list[Relation]:
        """Tạo mọi tổ hợp source × target sau khi tách các vế liệt kê."""
        sources = (
            self._decompose_factor(relation.source)
            if relation.source is not None
            else [None]
        )
        targets = (
            self._decompose_factor(relation.target)
            if relation.target is not None
            else [None]
        )
        return [
            Relation(
                source=src,
                trigger=relation.trigger,
                relationship=relation.relationship,
                target=tgt,
                confidence=relation.confidence,
            )
            for src in sources
            for tgt in targets
        ]

    # ── recursive decomposition ─────────────────────────────────

    def _decompose_factor(self, factor: Factor | None) -> list[Factor]:
        """Tách factor thành các factor nguyên tử (đệ quy)."""
        if factor is None:
            return []
        if not self._has_separator(factor):
            return [factor]

        # Ưu tiên 1: tách dấu phẩy + vị ngữ mới (clause-level).
        # Ưu tiên 2: tách coord/conj (within-clause coordination).
        parts = self._split_by_comma_verb(factor)
        if parts is None:
            parts = self._split_by_coordination(factor)
        if parts is None:
            return [factor]

        result: list[Factor] = []
        for sub in parts:
            result.extend(self._decompose_factor(sub))
        return result

    # ── helpers ──────────────────────────────────────────────────

    def _has_separator(self, factor: Factor) -> bool:
        """Factor có dấu phẩy hoặc liên từ ở giữa (bỏ qua đầu/cuối)."""
        tokens = [
            self.tree.get_token(tid)
            for tid in sorted(factor.token_ids)
        ]
        tokens = [t for t in tokens if t is not None]
        if len(tokens) < 3:
            return False
        return any(
            t.word.lower() in self._SEPARATORS
            for t in tokens[1:-1]
        )

    def _make_factor(self, ids: set[int] | list[int]) -> Factor | None:
        """Tạo Factor từ tập ID, loại punct ở hai đầu."""
        clean = sorted(self.tree.strip_edge_punct(ids))
        if not clean:
            return None
        return Factor(
            text=self.tree.surface(clean),
            token_ids=clean,
        )

    # ── Strategy 1: comma + verb ────────────────────────────────

    def _split_by_comma_verb(self, factor: Factor) -> list[Factor] | None:
        """Tách tại dấu phẩy khi ngay sau là vị ngữ mới (POS ``V``).

        Cho phép bỏ qua tối đa 1 token phụ từ/trạng từ (``R``) giữa
        dấu phẩy và vị ngữ, ví dụ ``", không gây …"``.

        Ví dụ đầu vào::

            giảm_thiểu hoá_chất độc_hại , cải_thiện môi_trường sống

        Kết quả::

            ["giảm_thiểu hoá_chất độc_hại",
             "cải_thiện môi_trường sống"]
        """
        indexed = self._indexed_tokens(factor)
        if not indexed:
            return None

        cuts: list[int] = []
        for i, (_, token) in enumerate(indexed):
            if token.word != ",":
                continue
            if self._verb_after(indexed, i):
                cuts.append(i)

        if not cuts:
            return None

        segments: list[Factor] = []
        start = 0
        for ci in cuts:
            seg_ids = [tid for tid, _ in indexed[start:ci]]
            fac = self._make_factor(seg_ids)
            if fac is not None:
                segments.append(fac)
            start = ci + 1          # bỏ dấu phẩy

        tail_ids = [tid for tid, _ in indexed[start:]]
        fac = self._make_factor(tail_ids)
        if fac is not None:
            segments.append(fac)

        if len(segments) <= 1:
            return None

        # ── Safety: mỗi segment phải có ít nhất 1 vị ngữ (V). ──
        # Segment không có V thường là discourse marker
        # ("Bên cạnh đó", "Song song đó", "Ngoài ra") hoặc cụm danh từ
        # rời rạc — tách ra sẽ tạo factor vô nghĩa.
        for seg in segments:
            if not self._has_verb(seg):
                return None

        return segments

    # ── Strategy 2: coord / conj ────────────────────────────────

    def _split_by_coordination(self, factor: Factor) -> list[Factor] | None:
        """Tách dựa trên quan hệ ``coord`` / ``conj`` trong dep tree.

        Dùng **span-based split** tại vị trí token ``coord`` để đảm bảo
        xử lý đúng cả liên kết danh từ lẫn liên kết mệnh đề.

        Ví dụ đầu vào (danh từ)::

            triển_khai phần_mềm và thiết_bị IoT

        Kết quả::

            ["triển_khai phần_mềm", "triển_khai thiết_bị IoT"]

        Shared prefix ``triển_khai`` được phân phối cho cả hai conjunct.

        Ví dụ đầu vào (mệnh đề)::

            phần_mềm thường_xuyên gián_đoạn và dữ_liệu không được đồng_bộ

        Kết quả::

            ["phần_mềm thường_xuyên gián_đoạn",
             "dữ_liệu không được đồng_bộ"]
        """
        factor_ids = set(factor.token_ids)

        coord_token, coord_head, conj_tokens = (
            self._find_first_coordination(factor_ids)
        )
        if coord_token is None:
            return None

        coord_pos = coord_token.id

        # ── xác định shared prefix ──
        if coord_head is not None:
            shared = self._shared_prefix(coord_head, factor_ids)
            first_ids = {
                tid for tid in factor_ids
                if coord_head.id <= tid < coord_pos
            }
        else:
            shared: set[int] = set()
            first_ids = {
                tid for tid in factor_ids
                if tid < coord_pos
            }

        rest_ids = {
            tid for tid in factor_ids
            if tid > coord_pos
        }

        # ── Safety: coordination phải bao phủ phần lớn factor. ──
        # Nếu có quá nhiều token nằm ngoài cả hai conjunct,
        # coordination bị nhúng quá sâu → tách sẽ sai.
        accounted = shared | first_ids | rest_ids | {coord_pos}
        non_punct_factor = {
            tid for tid in factor_ids
            if self.tree.get_token(tid)
            and self.tree.get_token(tid).pos != "CH"
        }
        unaccounted = non_punct_factor - accounted
        if len(unaccounted) > self._MAX_UNACCOUNTED:
            return None

        f1 = self._make_factor(shared | first_ids)
        f2 = self._make_factor(shared | rest_ids)
        parts = [f for f in (f1, f2) if f is not None]
        return parts if len(parts) > 1 else None

    # ── coordination utilities ──────────────────────────────────

    def _find_first_coordination(
        self,
        factor_ids: set[int],
    ) -> tuple[
        DependencyToken | None,
        DependencyToken | None,
        list[DependencyToken],
    ]:
        """Tìm token ``coord`` đầu tiên (trái → phải) trong factor.

        Returns
        -------
        (coord_token, coord_head_or_None, conj_children)
        """
        for tid in sorted(factor_ids):
            tok = self.tree.get_token(tid)
            if tok is None or tok.dep != "coord":
                continue
            conjs = [
                c for c in self.tree.find_children(tok)
                if c.dep == "conj" and c.id in factor_ids
            ]
            if not conjs:
                continue
            head = self.tree.get_token(tok.head)
            head_in = head if (head and head.id in factor_ids) else None
            return tok, head_in, conjs
        return None, None, []

    def _shared_prefix(
        self,
        coord_head: DependencyToken,
        factor_ids: set[int],
    ) -> set[int]:
        """Tìm vị ngữ / bổ ngữ chung đứng trước conjunct đầu.

        Chỉ lấy **cha trực tiếp** của coordination head (thường là vị ngữ
        chung) cùng các modifier của cha đó nằm trước coordination head.
        Không lấy toàn bộ span trước head để tránh kéo theo mệnh đề
        liệt kê trước đó (VD ``giảm_thiểu hoá_chất,`` không nên
        trở thành shared prefix của ``cải_thiện X và Y``).
        """
        shared: set[int] = set()
        parent = self.tree.find_parent(coord_head)
        if parent is None:
            return shared
        if parent.id not in factor_ids:
            return shared
        if parent.id >= coord_head.id:
            return shared

        shared.add(parent.id)

        for child in self.tree.find_children(parent):
            if (
                child.id in factor_ids
                and child.id < coord_head.id
                and child.dep not in {"coord", "conj", "punct"}
            ):
                shared.add(child.id)
        return shared

    # ── low-level helpers ───────────────────────────────────────

    def _has_verb(self, factor: Factor) -> bool:
        """Factor có chứa ít nhất một token POS ``V`` không."""
        return any(
            (tok := self.tree.get_token(tid)) is not None and tok.pos == "V"
            for tid in factor.token_ids
        )

    @staticmethod
    def _verb_after(
        indexed: list[tuple[int, DependencyToken]],
        comma_idx: int,
        lookahead: int = 2,
    ) -> bool:
        """Có vị ngữ ``V`` ngay sau dấu phẩy không (cho phép bỏ qua ``R``)."""
        end = min(comma_idx + 1 + lookahead, len(indexed))
        for j in range(comma_idx + 1, end):
            pos = indexed[j][1].pos
            if pos == "V":
                return True
            if pos != "R":
                return False
        return False

    def _indexed_tokens(
        self,
        factor: Factor,
    ) -> list[tuple[int, DependencyToken]]:
        """Danh sách (token_id, DependencyToken) theo thứ tự tuyến tính."""
        result = []
        for tid in sorted(factor.token_ids):
            tok = self.tree.get_token(tid)
            if tok is not None:
                result.append((tid, tok))
        return result