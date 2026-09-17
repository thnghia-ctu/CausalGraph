from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse

from app.services.dataset_store import dataset_dir, load_meta, save_meta
from app.services.graph_service import build_dataset_graph, load_graph_summary
from configs.config import CONCEPT_CLUSTER_DISTANCE_THRESHOLD
from src.concept_builder.concept_clustering import MIN_SENTENCE_COUNT

router = APIRouter()
template = Jinja2Templates(directory="app/frontend/templates")


@router.get("/graph")
def graph_visualize_page(request: Request):
    selected_data_id = request.session.get("data_id")
    selected_dataset_name = request.session.get("data_name")
    meta = load_meta(selected_data_id) if selected_data_id else None
    graph_path = (
        dataset_dir(selected_data_id) / "graph" / "concept_graph.html"
        if selected_data_id
        else None
    )
    graph_summary = load_graph_summary(dataset_dir(selected_data_id)) if selected_data_id else {
        "nodes": 0,
        "edges": 0,
        "visible_edges": 0,
        "available": False,
    }
    distance_threshold = (
        meta.last_distance_threshold
        if meta and meta.last_distance_threshold is not None
        else CONCEPT_CLUSTER_DISTANCE_THRESHOLD
    )
    min_edge_count = (
        meta.last_min_sentence_count
        if meta and meta.last_min_sentence_count is not None
        else MIN_SENTENCE_COUNT
    )

    return template.TemplateResponse(
        request=request,
        name="graph_visualize_page.html",
        context={
            "selected_data_id": selected_data_id,
            "selected_dataset_name": selected_dataset_name,
            "dataset": meta,
            "distance_threshold": distance_threshold,
            "min_edge_count": min_edge_count,
            "graph_preview": {
                "nodes": graph_summary["nodes"],
                "edges": graph_summary["edges"],
                "visible_edges": graph_summary["visible_edges"],
            },
            "graph_available": graph_summary["available"],
        },
    )


@router.get("/graph/visualization")
def graph_visualization(request: Request):
    selected_data_id = request.session.get("data_id")
    selected_dataset_name = request.session.get("data_name")
    if not selected_data_id:
        raise HTTPException(status_code=400, detail="Chưa chọn tập dữ liệu.")

    meta = load_meta(selected_data_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")

    try:
        threshold = float(request.query_params.get("distance_threshold", ""))
        min_edge_count = int(request.query_params.get("min_edge_count", ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Tham số đồ thị không hợp lệ.") from exc

    if not 0 <= threshold <= 1 or min_edge_count < 1:
        raise HTTPException(status_code=422, detail="Tham số đồ thị nằm ngoài giới hạn.")

    meta.last_distance_threshold = threshold
    meta.last_min_sentence_count = min_edge_count
    save_meta(meta)

    graph, graph_path = build_dataset_graph(
        dataset_dir(selected_data_id),
        distance_threshold=threshold,
        min_edge_count=min_edge_count,
    )

    return template.TemplateResponse(
        request=request,
        name="_graph_visualization.html",
        context={
            "selected_data_id": selected_data_id,
            "selected_dataset_name": selected_dataset_name,
            "distance_threshold": threshold,
            "min_edge_count": min_edge_count,
            "graph_preview": {
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "visible_edges": graph.number_of_edges(),
            },
            "graph_available": graph_path.exists(),
        },
    )


@router.get("/graph/render")
def graph_render(request: Request):
    selected_data_id = request.session.get("data_id")
    if not selected_data_id:
        raise HTTPException(status_code=400, detail="Chưa chọn tập dữ liệu.")

    graph_path = dataset_dir(selected_data_id) / "graph" / "concept_graph.html"
    if not graph_path.exists():
        raise HTTPException(status_code=404, detail="Chưa có đồ thị cho tập dữ liệu.")
    return FileResponse(graph_path, media_type="text/html")
