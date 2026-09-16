from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from charset_normalizer import from_bytes

from app.constants.cons import (
    STEP_CHUNK,
    STEP_CRAWL,
    STEP_LABELS,
    STEP_NONE,
)

from app.services.dataset_store import (
    create_dataset as create_dataset_record,
    dataset_dir,
    delete_dataset as delete_dataset_record,
    load_source_urls,
    load_meta,
    list_datasets,
    get_progress,
    get_status_label,
    save_meta,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/frontend/templates")


def _dataset_response(meta):
    return {
        "id": meta.id,
        "name": meta.name,
        "status": meta.status,
        "status_label": get_status_label(meta),
        "step": meta.step,
        "step_label": STEP_LABELS.get(meta.step, ""),
        "progress": get_progress(meta),
        "stage_counts": meta.stage_counts,
        "error": meta.error,
    }


def _progress_context(meta):
    return {
        **meta.__dict__,
        "status_label": get_status_label(meta),
        "step_label": STEP_LABELS.get(meta.step, ""),
        "progress": get_progress(meta),
    }


def _crawl_dataset(dataset_id: str) -> None:
    from src.crawlers.crawl_runner import load_documents
    from src.pipeline import Pipeline

    meta = load_meta(dataset_id)
    if meta is None:
        return

    try:
        pipeline = Pipeline()
        output_dir = dataset_dir(dataset_id)

        meta.step = STEP_CRAWL
        save_meta(meta)
        pipeline.crawl_data(load_source_urls(dataset_id), output_path=output_dir)
        documents = load_documents(output_dir)
        meta.stage_counts["crawl"] = len(documents)
        save_meta(meta)

        meta.step = STEP_CHUNK
        save_meta(meta)
        chunks = pipeline.chunk_data(documents, output_path=output_dir)
        meta.stage_counts["chunk"] = len(chunks)
        meta.status = 1
        meta.step = STEP_NONE
    except Exception as error:
        meta.status = -1
        meta.error = str(error)

    save_meta(meta)


@router.delete("/api/datasets/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str):
    if load_meta(dataset_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")
    delete_dataset_record(dataset_id)


@router.get("/api/datasets")
def get_datasets():
    return [
        {
            "id": meta.id,
            "name": meta.name,
            "status": meta.status,
            "status_label": get_status_label(meta),
            "step": meta.step,
            "step_label": STEP_LABELS.get(meta.step, ""),
            "created_at": meta.created_at,
            "source_url_count": meta.source_url_count,
        }
        for meta in list_datasets()
    ]


@router.get("/api/datasets/{dataset_id}/status")
def get_dataset_status(dataset_id: str):
    meta = load_meta(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")
    return _dataset_response(meta)


@router.get("/datasets/{dataset_id}/progress", response_class=HTMLResponse)
def dataset_progress(dataset_id: str, request: Request):
    meta = load_meta(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")
    return templates.TemplateResponse(
        request=request,
        name="datasets/_progress.html",
        context={"dataset": _progress_context(meta)},
    )


@router.post("/api/datasets/{dataset_id}/crawl", status_code=202)
def crawl_dataset(
    dataset_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
):
    meta = load_meta(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")

    if meta.status == 2:
        raise HTTPException(status_code=409, detail="Tập dữ liệu đang được xử lý.")

    urls = load_source_urls(dataset_id)
    if not urls:
        raise HTTPException(status_code=400, detail="Tập dữ liệu chưa có URL nguồn.")

    meta.status = 2
    meta.step = STEP_CRAWL
    meta.error = ""
    meta.stage_counts = {}
    save_meta(meta)
    background_tasks.add_task(_crawl_dataset, dataset_id)
    return templates.TemplateResponse(
        request=request,
        name="datasets/_progress.html",
        context={"dataset": _progress_context(meta)},
    )


@router.post("/api/datasets")
async def create_dataset(
    data_name: str = Form(...),
    description: str = Form(""),
    data_file: UploadFile = File(...),
):
    name = data_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Cần nhập tên tập dữ liệu.")

    raw_bytes = await data_file.read()
    match = from_bytes(raw_bytes).best()
    if match is None:
        raise HTTPException(
            status_code=400,
            detail="Không đọc được encoding của file danh sách URL.",
        )

    urls = list(dict.fromkeys(line.strip() for line in str(match).splitlines() if line.strip()))
    if not urls:
        raise HTTPException(status_code=400, detail="Cần tải lên file danh sách URL.")

    create_dataset_record(name, urls)
    return RedirectResponse(url="/", status_code=303)