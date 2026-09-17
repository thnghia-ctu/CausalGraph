from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.constants.cons import STEP_LABELS
from app.services.dataset_store import (
    get_progress,
    get_stage_progress,
    get_status_label,
    list_datasets,
)

router = APIRouter()

template = Jinja2Templates(directory="app/frontend/templates")

@router.get("/")
def home(request: Request):
    selected_data_id = request.session.get("data_id")
    datasets = [
        {
            "id": meta.id,
            "name": meta.name,
            "status": meta.status,
            "status_label": get_status_label(meta),
            "step": meta.step,
            "step_label": STEP_LABELS.get(meta.step, ""),
            "stage_counts": meta.stage_counts,
            "error": meta.error,
            "progress": get_progress(meta),
            "stage_progress": get_stage_progress(meta),
            "created_at": meta.created_at,
            "source_url_count": meta.source_url_count,
        }
        for meta in list_datasets()
    ]
    selected_dataset_name = request.session.get("data_name")

    return template.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "datasets": datasets,
            "selected_data_id": selected_data_id,
            "selected_dataset_name": selected_dataset_name,
        },
    )