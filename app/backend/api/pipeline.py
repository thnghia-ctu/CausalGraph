from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from app.services.dataset_store import load_meta, save_meta
from app.services.pipeline_service import PipelineService, get_progress
from app.constants.cons import (
    STATUS_INGESTING,
    STATUS_SUCCESS,
    STEP_CAUSAL_DETECTION,
    STEP_LABELS,
    STEP_CONCEPT_STATE,
)

router = APIRouter()
template = Jinja2Templates(directory="app/frontend/templates")
pipeline_service = PipelineService()

PROCESS_STAGES = (
    ("causal_detect", "Nhận diện câu nhân quả", "Tìm các câu có quan hệ nhân quả trong chunk đã lọc."),
    ("simplify", "Tách câu đơn", "Chuẩn hóa và tách câu phức thành các câu đơn."),
    ("spo", "Trích xuất SPO", "Xác định subject, predicate và object trong câu."),
    ("concept_state", "Phân rã concept/state", "Tách concept và trạng thái để dựng dữ liệu đồ thị."),
)


@router.post("/api/pipeline/{dataset_id}/run-pipeline")
def run_pipeline(dataset_id: str, background_tasks: BackgroundTasks):
    meta = load_meta(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")
    
    # if meta.status == STATUS_INGESTING:
    #     raise HTTPException(
    #         status_code=409,
    #         detail="Pipeline đang được xử lý.",
    #     )
    
    if meta.step < STEP_CAUSAL_DETECTION or (meta.step == STEP_CONCEPT_STATE and meta.status == STATUS_SUCCESS):
        meta.step = STEP_CAUSAL_DETECTION
        process_stage_keys = {stage_key for stage_key, _, _ in PROCESS_STAGES}
        for stage_key in process_stage_keys:
            meta.stage_counts.pop(stage_key, None)

    meta.status = STATUS_INGESTING
    meta.error = ""
    save_meta(meta)

    background_tasks.add_task(pipeline_service.process, dataset_id)
    return Response(status_code=200, headers={"HX-Redirect": "/ingest"})

@router.get("/api/pipeline/{dataset_id}/status")
def get_pipeline_status(dataset_id: str, request: Request):
    meta = load_meta(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")

    selected_data_id = request.session.get("data_id")
    selected_dataset_name = request.session.get("data_name")
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
            name="_pipeline_progress.html",
            context={
                "selected_data_id": selected_data_id,
                "selected_dataset_name": selected_dataset_name,
                "dataset": meta,
                "stages": stages,
                "step_label": STEP_LABELS.get(meta.step, "") if meta else "",
                "progress": get_progress(dataset_id),
            },
        )
