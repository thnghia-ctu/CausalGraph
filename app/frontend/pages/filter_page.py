from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.constants.cons import STEP_FILTER, STEP_LABELS, STATUS_INGESTING, STATUS_SUCCESS
from app.services.filter_config_store import get_filter_progress, load_filter_config
from app.services.dataset_store import get_status_label, load_meta
from configs.config import CHUNK_FILTER_THRESHOLD

router = APIRouter()
template = Jinja2Templates(directory="app/frontend/templates")

@router.get("/filter")
def filter_page(request: Request):
    selected_data_id = request.session.get("data_id")
    selected_dataset_name = request.session.get("data_name")
    meta = load_meta(selected_data_id) if selected_data_id else None
    progress = get_filter_progress(selected_data_id) if selected_data_id else {
        "processed": 0,
        "total": 0,
        "kept": 0,
        "rejected": 0,
        "remaining": 0,
        "progress": 0,
    }
    filter_config = load_filter_config(selected_data_id) if selected_data_id else {
        "lexicon": [],
        "query": [],
        "threshold": CHUNK_FILTER_THRESHOLD,
    }
    return template.TemplateResponse(
        request=request,
        name="filter_page.html",
        context={
            "selected_data_id": selected_data_id,
            "selected_dataset_name": selected_dataset_name,
            "lexicon": filter_config["lexicon"],
            "query": filter_config["query"],
            "threshold": filter_config["threshold"],
            "filter_step_filter": STEP_FILTER,
            "filter_status_ingesting": STATUS_INGESTING,
            "filter_status": {
                "dataset_id": selected_data_id,
                "step": meta.step if meta else 0,
                "step_label": STEP_LABELS.get(meta.step, "") if meta else "",
                "status": meta.status if meta else STATUS_SUCCESS,
                "status_label": get_status_label(meta) if meta else "",
                **progress,
            },
        },
    )