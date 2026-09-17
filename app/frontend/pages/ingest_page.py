from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.constants.cons import STATUS_INGESTING, STEP_LABELS
from app.services.dataset_store import load_meta
from app.services.pipeline_service import get_progress

router = APIRouter()
template = Jinja2Templates(directory="app/frontend/templates")

PROCESS_STAGES = (
    ("causal_detect", "Nhận diện câu nhân quả", "Tìm các câu có quan hệ nhân quả trong chunk đã lọc."),
    ("simplify", "Tách câu đơn", "Chuẩn hóa và tách câu phức thành các câu đơn."),
    ("spo", "Trích xuất SPO", "Xác định subject, predicate và object trong câu."),
    ("concept_state", "Phân rã concept/state", "Tách concept và trạng thái để dựng dữ liệu đồ thị."),
)


@router.get("/ingest")
def ingest_page(request: Request):
    selected_data_id = request.session.get("data_id")
    selected_dataset_name = request.session.get("data_name")
    meta = load_meta(selected_data_id) if selected_data_id else None
    stage_counts = meta.stage_counts if meta else {}
    active_stage = next(
        (stage_key for stage_key, _, _ in PROCESS_STAGES if stage_key not in stage_counts),
        None,
    )

    stages = [
        {
            "key": stage_key,
            "label": stage_label,
            "description": description,
            "count": stage_counts.get(stage_key),
            "active": meta is not None and meta.status == STATUS_INGESTING and stage_key == active_stage,
        }
        for stage_key, stage_label, description in PROCESS_STAGES
    ]

    return template.TemplateResponse(
        request=request,
        name="ingest_page.html",
        context={
            "selected_data_id": selected_data_id,
            "selected_dataset_name": selected_dataset_name,
            "dataset": meta,
            "stages": stages,
            "step_label": STEP_LABELS.get(meta.step, "") if meta else "",
            "progress": get_progress(selected_data_id),
        },
    )
