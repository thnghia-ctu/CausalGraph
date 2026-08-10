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
from services.pipeline_service import PROCESS_STAGES, STAGE_LABELS, get_pipeline_service

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

stage_placeholders = {}
for stage_key, stage_label in PROCESS_STAGES:
    stage_placeholders[stage_key] = st.empty()
    count = meta.stage_counts.get(stage_key)
    stage_placeholders[stage_key].write(
        f"✅ {stage_label}: {count}" if count is not None else f"⏳ {stage_label}"
    )

st.divider()

button_label = "Chạy lại pipeline" if meta.status == STATUS_READY else "Bắt đầu xử lý pipeline"
if st.button(button_label, type="primary"):
    meta.status = STATUS_INGESTING
    meta.error = ""
    save_meta(meta)

    for stage_key, stage_label in PROCESS_STAGES:
        meta.stage_counts.pop(stage_key, None)
        stage_placeholders[stage_key].write(f"⏳ {stage_label}")

    service = get_pipeline_service()

    def on_progress(stage_key: str, count: int) -> None:
        meta.stage_counts[stage_key] = count
        save_meta(meta)
        stage_placeholders[stage_key].write(f"✅ {STAGE_LABELS[stage_key]}: {count}")

    try:
        with st.spinner("Đang chạy pipeline..."):
            service.process(dataset_dir(dataset_id), on_progress=on_progress)
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
    "Thu thập, phân đoạn và lọc dữ liệu đã thực hiện ở các bước trước. Chạy lại ở đây sẽ xử lý lại từ "
    "dữ liệu đã lọc, các bước sau luôn ghi đè kết quả cũ."
)
