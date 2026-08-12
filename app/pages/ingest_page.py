import streamlit as st

from services.dataset_store import (
    STATUS_FAILED,
    STATUS_INGESTING,
    STATUS_LABELS,
    STATUS_NEW,
    STATUS_READY,
    dataset_dir,
    load_meta,
    save_meta,
)
from services.pipeline_service import PROCESS_STAGES, get_pipeline_service

st.title("Bước 2 — Xử lý dữ liệu")

dataset_id = st.session_state.get("dataset_id")
if not dataset_id:
    st.warning("Chưa chọn tập dữ liệu nào.")
    if st.button("← Quay lại chọn tập dữ liệu"):
        st.switch_page("pages/index_page.py")
    st.stop()

meta = load_meta(dataset_id)
if meta is None:
    st.error(f"Không tìm thấy tập dữ liệu '{dataset_id}'.")
    st.stop()

if meta.status == STATUS_NEW:
    st.warning("Tập dữ liệu chưa được thu thập dữ liệu. Quay lại trang danh sách để bấm Tải dữ liệu trước.")
    if st.button("← Quay lại chọn tập dữ liệu"):
        st.switch_page("pages/index_page.py")
    st.stop()

if not (dataset_dir(dataset_id) / "chunks" / "chunks_filtered.jsonl").exists():
    st.warning("Chưa có dữ liệu đã lọc. Hãy chạy 'Lọc dữ liệu' trước.")
    if st.button("→ Sang trang Lọc dữ liệu"):
        st.switch_page("pages/filter_page.py")
    st.stop()

st.subheader(meta.name)
st.caption(f"ID: `{meta.id}` · Tạo lúc: {meta.created_at[:19].replace('T', ' ')}")

info_cols = st.columns(2)
info_cols[0].metric("Trạng thái", STATUS_LABELS.get(meta.status, meta.status))
info_cols[1].metric("Số văn bản đã thu thập", meta.stage_counts.get("crawl", 0))

if meta.status == STATUS_FAILED and meta.error:
    st.error(f"Lần chạy trước lỗi: {meta.error}")

st.divider()
st.subheader("Các bước xử lý")

STAGE_OUTPUT_FILES = {
    "causal_detect": ("causal_sentences", "causal_sentences.csv"),
    "simplify": ("simplified", "simplified_sentences.csv"),
    "spo": ("spo", "spo_relations.csv"),
    "concept_state": ("concept_state", "concept_state_relations.csv"),
}


def _row_count(path) -> int:
    return max(sum(1 for _ in open(path)) - 1, 0)


@st.fragment(run_every="2s", parallel=True)
def show_stage_progress():
    active_stage = next((key for key, _ in PROCESS_STAGES if key not in meta.stage_counts), None)
    for stage_key, stage_label in PROCESS_STAGES:
        count = meta.stage_counts.get(stage_key)
        if count is not None:
            st.write(f"✅ {stage_label}: {count}")
            continue

        if meta.status == STATUS_INGESTING and stage_key == active_stage:
            subdir, filename = STAGE_OUTPUT_FILES[stage_key]
            path = dataset_dir(dataset_id) / subdir / filename
            if path.exists():
                st.write(f"⏳ {stage_label}: {_row_count(path)}")
                continue

        st.write(f"⏳ {stage_label}")


show_stage_progress()

st.divider()

PROCESS_STAGE_KEYS = {stage_key for stage_key, _ in PROCESS_STAGES}
resuming = meta.status != STATUS_READY and bool(set(meta.stage_counts) & PROCESS_STAGE_KEYS)

if meta.status == STATUS_READY:
    button_label = "Chạy lại pipeline"
elif resuming:
    button_label = "Tiếp tục xử lý pipeline"
else:
    button_label = "Bắt đầu xử lý pipeline"

if st.button(button_label, type="primary"):
    completed_stages = set(meta.stage_counts) & PROCESS_STAGE_KEYS if resuming else set()

    meta.status = STATUS_INGESTING
    meta.error = ""
    for stage_key, _ in PROCESS_STAGES:
        if stage_key not in completed_stages:
            meta.stage_counts.pop(stage_key, None)
    save_meta(meta)

    service = get_pipeline_service()

    def on_progress(stage_key: str, count: int) -> None:
        meta.stage_counts[stage_key] = count
        save_meta(meta)

    try:
        with st.spinner("Đang chạy pipeline..."):
            service.process(dataset_dir(dataset_id), on_progress=on_progress, completed_stages=completed_stages)
    except Exception as error:
        meta.status = STATUS_FAILED
        meta.error = str(error)
        save_meta(meta)
        st.error(f"Lỗi khi xử lý pipeline: {error}")
        st.stop()

    meta.status = STATUS_READY
    save_meta(meta)
    st.success("Đã xử lý xong pipeline.")
    st.rerun()

st.caption(
    "Thu thập, phân đoạn và lọc dữ liệu đã thực hiện ở các bước trước. Nếu pipeline đang dang dở, bấm nút sẽ "
    "chạy tiếp từ bước chưa hoàn thành; nếu đã xong toàn bộ, bấm sẽ chạy lại từ đầu và ghi đè kết quả cũ."
)
