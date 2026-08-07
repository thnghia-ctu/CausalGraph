import streamlit as st

from services.dataset_store import (
    STATUS_FAILED,
    STATUS_INGESTING,
    STATUS_LABELS,
    STATUS_READY,
    dataset_dir,
    load_meta,
    load_source_urls,
    save_meta,
)
from services.pipeline_service import STAGE_LABELS, STAGES, get_pipeline_service
from src.crawlers.crawl_runner import load_documents

st.title("Bước 2 — Xử lý dữ liệu")

dataset_id = st.session_state.get("dataset_id")
if not dataset_id:
    st.warning("Chưa chọn dataset nào.")
    if st.button("← Quay lại chọn dataset"):
        st.switch_page("pages/index_page.py")
    st.stop()

meta = load_meta(dataset_id)
if meta is None:
    st.error(f"Không tìm thấy dataset '{dataset_id}'.")
    st.stop()

uploaded_document_count = sum(
    1 for doc in load_documents(dataset_dir(dataset_id)) if doc.source_type == "upload"
)

st.subheader(meta.name)
st.caption(f"ID: `{meta.id}` · Tạo lúc: {meta.created_at[:19].replace('T', ' ')}")

info_cols = st.columns(3)
info_cols[0].metric("Trạng thái", STATUS_LABELS.get(meta.status, meta.status))
info_cols[1].metric("Số URL", meta.source_url_count)
info_cols[2].metric("Số file đã tải lên", uploaded_document_count)

if meta.status == STATUS_FAILED and meta.error:
    st.error(f"Lần chạy trước lỗi: {meta.error}")

st.divider()
st.subheader("Các bước xử lý")

for stage_key, stage_label in STAGES:
    count = meta.stage_counts.get(stage_key)
    st.write(f"✅ {stage_label}: {count}" if count is not None else f"⏳ {stage_label}")

st.divider()

button_label = "Chạy lại pipeline" if meta.status == STATUS_READY else "Bắt đầu xử lý pipeline"
if st.button(button_label, type="primary"):
    urls = load_source_urls(dataset_id)
    meta.status = STATUS_INGESTING
    meta.error = ""
    save_meta(meta)

    service = get_pipeline_service()

    with st.status("Đang xử lý pipeline...", expanded=True) as status_box:
        def on_progress(stage_key: str, count: int) -> None:
            meta.stage_counts[stage_key] = count
            save_meta(meta)
            st.write(f"✅ {STAGE_LABELS[stage_key]}: {count}")

        try:
            service.ingest(urls, dataset_dir(dataset_id), on_progress=on_progress)
        except Exception as error:
            meta.status = STATUS_FAILED
            meta.error = str(error)
            save_meta(meta)
            status_box.update(label="Xử lý lỗi", state="error")
            st.exception(error)
            st.stop()

        meta.status = STATUS_READY
        save_meta(meta)
        status_box.update(label="Hoàn tất", state="complete")

    st.success("Đã xử lý xong pipeline.")
    st.rerun()

st.caption(
    "Chạy lại sẽ xử lý lại toàn bộ từ đầu (crawl chỉ bỏ qua URL đã tải, "
    "các bước sau luôn ghi đè kết quả cũ)."
)

if meta.status == STATUS_READY:
    if st.sidebar.button("Sang bước 3: Khám phá đồ thị →", type="primary"):
        st.switch_page("pages/explore_page.py")
