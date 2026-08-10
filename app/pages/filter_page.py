import pandas as pd
import streamlit as st

from configs.config import CHUNK_FILTER_THRESHOLD
from services.dataset_store import dataset_dir, load_meta
from services.pipeline_service import get_pipeline_service
from src.chunking.chunk_runner import load_chunks
from src.filtering.knowledge_base_store import load_knowledge_base, save_knowledge_base

st.title("Lọc dữ liệu")

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

st.subheader(meta.name)

knowledge_base = load_knowledge_base(dataset_dir(dataset_id))

with st.expander("Lexicon — các từ khóa liên quan dùng để chấm điểm chunk"):
    lexicon_df = st.data_editor(
        pd.DataFrame({"lexicon": knowledge_base["lexicon"]}),
        num_rows="dynamic",
        height=250,
        key="lexicon_editor",
    )

with st.expander("Query — các câu hỏi mẫu dùng để chấm điểm chunk"):
    query_df = st.data_editor(
        pd.DataFrame({"query": knowledge_base["query"]}),
        num_rows="dynamic",
        height=250,
        key="query_editor",
    )

threshold = st.slider(
    "Ngưỡng lọc (threshold)",
    min_value=0.0,
    max_value=1.0,
    value=knowledge_base.get("threshold", CHUNK_FILTER_THRESHOLD),
    step=0.01,
)

def _current_knowledge_base() -> dict:
    lexicon_values = lexicon_df["lexicon"].dropna().astype(str).str.strip()
    query_values = query_df["query"].dropna().astype(str).str.strip()
    return {
        "lexicon": [v for v in lexicon_values if v],
        "query": [v for v in query_values if v],
        "threshold": threshold,
    }


if st.button("Lưu", type="secondary"):
    save_knowledge_base(dataset_dir(dataset_id), _current_knowledge_base())
    st.success("Đã lưu knowledge base.")
    st.rerun()

st.divider()

@st.fragment(run_every="2s", parallel=True)
def show_filter_progress():
    chunks_dir = dataset_dir(dataset_id) / "chunks"
    total_path = chunks_dir / "chunks.jsonl"
    if not total_path.exists():
        return

    total = sum(1 for _ in open(total_path))
    if total == 0:
        return

    done = 0
    for filename in ("chunks_filtered.jsonl", "chunks_rejected.jsonl"):
        path = chunks_dir / filename
        if path.exists():
            done += sum(1 for _ in open(path))

    st.progress(min(done / total, 1.0), text=f"Đang lọc: {done}/{total}")


show_filter_progress()

if st.button("Lọc dữ liệu", type="primary"):
    chunks = load_chunks(dataset_dir(dataset_id))
    if not chunks:
        st.warning("Chưa có chunk nào — cần chạy 'Thu thập dữ liệu' trước.")
    else:
        save_knowledge_base(dataset_dir(dataset_id), _current_knowledge_base())
        service = get_pipeline_service()
        with st.spinner("Đang lọc dữ liệu..."):
            filtered = service.filter(dataset_dir(dataset_id))
        st.success(f"Đã lọc xong: {len(filtered)}/{len(chunks)} chunk được giữ lại.")
