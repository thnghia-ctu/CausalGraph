import streamlit as st

from services.dataset_store import STATUS_LABELS, load_meta
from services.pipeline_service import STAGES

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

st.subheader(meta.name)
st.caption(f"ID: `{meta.id}` · Tạo lúc: {meta.created_at[:19].replace('T', ' ')}")

info_cols = st.columns(3)
info_cols[0].metric("Trạng thái", STATUS_LABELS.get(meta.status, meta.status))
info_cols[1].metric("Số URL", len(meta.source_urls))
info_cols[2].metric("Số file đã tải lên", 0)

st.divider()
st.subheader("Các bước xử lý")

for stage_key, stage_label in STAGES:
    st.write(f"⏳ {stage_label}")

st.divider()
st.button("Bắt đầu xử lý pipeline", type="primary", disabled=True)
st.caption("Chỗ giữ trước — sẽ nối vào PipelineService.ingest() ở bước triển khai chi tiết tiếp theo.")
