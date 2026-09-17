from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.services.dataset_store import load_meta

router = APIRouter()
template = Jinja2Templates(directory="app/frontend/templates")


@router.get("/graph")
def graph_visualize_page(request: Request):
    selected_data_id = request.session.get("data_id")
    selected_dataset_name = request.session.get("data_name")
    meta = load_meta(selected_data_id) if selected_data_id else None

    return template.TemplateResponse(
        request=request,
        name="graph_visualize_page.html",
        context={
            "selected_data_id": selected_data_id,
            "selected_dataset_name": selected_dataset_name,
            "dataset": meta,
            "distance_threshold": 0.65,
            "min_edge_count": 2,
            "graph_preview": {
                "nodes": 24,
                "edges": 31,
                "visible_edges": 18,
            },
        },
    )


@router.get("/graph/visualization")
def graph_visualization(request: Request):
    """Render-only HTMX target; graph data will be connected later."""
    threshold = float(request.query_params.get("distance_threshold", 0.65))
    min_edge_count = int(request.query_params.get("min_edge_count", 2))
    selected_data_id = request.session.get("data_id")
    selected_dataset_name = request.session.get("data_name")

    return template.TemplateResponse(
        request=request,
        name="_graph_visualization.html",
        context={
            "selected_data_id": selected_data_id,
            "selected_dataset_name": selected_dataset_name,
            "distance_threshold": threshold,
            "min_edge_count": min_edge_count,
            "graph_preview": {
                "nodes": 24,
                "edges": 31,
                "visible_edges": 18,
            },
        },
    )
