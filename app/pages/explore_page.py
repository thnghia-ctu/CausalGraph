import streamlit as st

from services.dataset_store import STATUS_READY, dataset_dir, load_meta, save_meta
from services.graph_service import GraphViewConfig, build_graph, load_spo_records

st.title("Bước 3 — Khám phá đồ thị")

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

if meta.status != STATUS_READY:
    st.warning("Tập dữ liệu chưa xử lý xong ở bước Xử lý dữ liệu. Hãy chạy pipeline trước.")
    if st.button("← Sang bước Xử lý dữ liệu"):
        st.switch_page("pages/ingest_page.py")
    st.stop()

data_dir = dataset_dir(dataset_id)
csv_path = data_dir / "concept_state" / "concept_state_relations.csv"
cache_bust = csv_path.stat().st_mtime if csv_path.exists() else 0.0
spo_records = load_spo_records(str(data_dir), cache_bust)

if not spo_records:
    st.info("Chưa có dữ liệu quan hệ nào để dựng đồ thị.")
    st.stop()

st.sidebar.subheader("Tham số đồ thị")

default_config = GraphViewConfig()
distance_threshold = st.sidebar.slider(
    "Ngưỡng gom nhóm concept",
    min_value=0.0,
    max_value=1.0,
    value=meta.last_distance_threshold or default_config.distance_threshold,
    step=0.01,
    help="Càng thấp càng chỉ gộp các concept_candidate rất giống nhau; càng cao càng gộp rộng.",
)
min_sentence_count = st.sidebar.slider(
    "Số câu nguồn độc lập tối thiểu trên mỗi cạnh",
    min_value=1,
    max_value=10,
    value=meta.last_min_sentence_count or default_config.min_sentence_count,
    step=1,
    help="Cạnh nào có ít hơn số câu nguồn độc lập này sẽ bị lọc khỏi đồ thị.",
)

config = GraphViewConfig(distance_threshold=distance_threshold, min_sentence_count=min_sentence_count)
graph = build_graph(spo_records, str(data_dir), config)

if (meta.last_distance_threshold, meta.last_min_sentence_count) != (distance_threshold, min_sentence_count):
    meta.last_distance_threshold = distance_threshold
    meta.last_min_sentence_count = min_sentence_count
    save_meta(meta)

st.caption(f"{graph.number_of_nodes()} concept · {graph.number_of_edges()} cạnh tổng hợp")

html_path = data_dir / "graph" / "concept_graph.html"
if html_path.exists():
    st.iframe(html_path, height="content")
else:
    st.info("Chưa có file đồ thị để hiển thị.")
