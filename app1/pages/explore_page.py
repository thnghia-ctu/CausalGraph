import pandas as pd
import streamlit as st

from services.dataset_store import STATUS_READY, dataset_dir, load_meta, save_meta
from services.graph_service import GraphViewConfig, build_graph, load_spo_records
from src.graph.edge_review_report import build_report

REPORT_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

title_col, download_col = st.columns([5, 1], vertical_alignment="center")
with title_col:
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
graph_dir = data_dir / "graph"
csv_path = data_dir / "concept_state" / "concept_state_relations.csv"
cache_bust = csv_path.stat().st_mtime if csv_path.exists() else 0.0
spo_records = load_spo_records(str(data_dir), cache_bust)

if not spo_records:
    st.info("Chưa có dữ liệu quan hệ nào để dựng đồ thị.")
    st.stop()

st.sidebar.subheader("Tham số đồ thị")

default_config = GraphViewConfig()
is_building = st.session_state.get("graph_is_building", False)

distance_threshold = st.sidebar.slider(
    "Ngưỡng gom nhóm concept",
    min_value=0.0,
    max_value=1.0,
    value=meta.last_distance_threshold or default_config.distance_threshold,
    step=0.01,
    help="Càng thấp càng chỉ gộp các concept_candidate rất giống nhau; càng cao càng gộp rộng.",
    disabled=is_building,
)
min_sentence_count = st.sidebar.slider(
    "Số câu nguồn độc lập tối thiểu trên mỗi cạnh",
    min_value=1,
    max_value=10,
    value=meta.last_min_sentence_count or default_config.min_sentence_count,
    step=1,
    help="Cạnh nào có ít hơn số câu nguồn độc lập này sẽ bị lọc khỏi đồ thị.",
    disabled=is_building,
)

apply_clicked = st.sidebar.button("Áp dụng", disabled=is_building)

if apply_clicked:
    st.session_state.graph_pending_config = GraphViewConfig(
        distance_threshold=distance_threshold,
        min_sentence_count=min_sentence_count,
    )
    st.session_state.graph_is_building = True
    st.rerun()

if is_building:
    with st.spinner("Đang dựng lại đồ thị..."):
        pending_config = st.session_state.graph_pending_config
        meta.last_distance_threshold = pending_config.distance_threshold
        meta.last_min_sentence_count = pending_config.min_sentence_count
        save_meta(meta)
        build_graph(spo_records, str(data_dir), pending_config)

        relations = pd.read_csv(graph_dir / "relations_with_concept.csv")
        concepts = pd.read_json(graph_dir / "concepts.jsonl", lines=True)
        build_report(
            relations, concepts, graph_dir / "edge_review_report.xlsx",
            min_sentence_count=pending_config.min_sentence_count,
        )
    st.session_state.graph_is_building = False
    st.rerun()

committed_config = GraphViewConfig(
    distance_threshold=meta.last_distance_threshold or default_config.distance_threshold,
    min_sentence_count=meta.last_min_sentence_count or default_config.min_sentence_count,
)
graph = build_graph(spo_records, str(data_dir), committed_config)

st.caption(f"{graph.number_of_nodes()} concept · {graph.number_of_edges()} cạnh tổng hợp")

report_path = graph_dir / "edge_review_report.xlsx"
with download_col:
    if report_path.exists():
        st.download_button(
            "Tải báo cáo",
            data=report_path.read_bytes(),
            file_name="edge_review_report.xlsx",
            mime=REPORT_MIME,
            disabled=is_building,
        )

html_path = graph_dir / "concept_graph.html"
if html_path.exists():
    st.iframe(html_path, height="content")
else:
    st.info("Chưa có file đồ thị để hiển thị.")
