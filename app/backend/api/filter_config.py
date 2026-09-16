from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse, Response

from app.constants.cons import STATUS_FAILED, STATUS_INGESTING, STATUS_SUCCESS, STEP_FILTER, STEP_LABELS

from app.services.filter_config_store import (
	default_filter_config,
	get_filter_progress,
	save_filter_config as save_filter_config_record,
	reset_filter_outputs,
)
from app.services.dataset_store import dataset_dir, load_meta, save_meta

router = APIRouter()
templates = Jinja2Templates(directory="app/frontend/templates")


class FilterConfigPayload(BaseModel):
	lexicon: list[str] = Field(default_factory=list)
	query: list[str] = Field(default_factory=list)
	threshold: float = Field(default=0.38, ge=0, le=1)


def _split_lines(value: str) -> list[str]:
	return [line.strip() for line in value.splitlines() if line.strip()]


@router.post("/api/datasets/{dataset_id}/filter-config/default")
def set_default_filter_config(dataset_id: str):
	config = default_filter_config()
	save_filter_config_record(dataset_id, config)
	return Response(status_code=200, headers={"HX-Redirect": "/filter"})


@router.post("/api/datasets/{dataset_id}/filter-config")
def save_filter_config(
	dataset_id: str,
	lexicon: str = Form(""),
	query: str = Form(""),
	threshold: float = Form(0.38),
):
	config = FilterConfigPayload(
		lexicon=_split_lines(lexicon),
		query=_split_lines(query),
		threshold=threshold,
	)
	save_filter_config_record(dataset_id, config.model_dump())
	return RedirectResponse(url="/filter", status_code=303)


@router.post("/api/datasets/{dataset_id}/filter")
def run_filter(dataset_id: str, background_tasks: BackgroundTasks):
	meta = load_meta(dataset_id)
	if meta is None:
		raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")

	can_resume = meta.step == STEP_FILTER and meta.status == STATUS_INGESTING
	if meta.status == STATUS_INGESTING and not can_resume:
		raise HTTPException(status_code=409, detail="Tập dữ liệu đang được xử lý.")

	from src.chunking.chunk_runner import load_chunks

	if not load_chunks(dataset_dir(dataset_id)):
		raise HTTPException(status_code=400, detail="Tập dữ liệu chưa có chunk nào.")

	if not can_resume:
		reset_filter_outputs(dataset_id)

	meta.step = STEP_FILTER
	meta.status = STATUS_INGESTING
	meta.error = ""
	save_meta(meta)
	background_tasks.add_task(_run_filter_task, dataset_id)
	return Response(status_code=200, headers={"HX-Redirect": "/filter"})


@router.get("/api/datasets/{dataset_id}/filter/status")
def get_status(dataset_id: str, request: Request):
	meta = load_meta(dataset_id)
	if meta is None:
		raise HTTPException(status_code=404, detail="Không tìm thấy tập dữ liệu.")

	progress = get_filter_progress(dataset_id)

	status = {
		"dataset_id": dataset_id,
		"step": meta.step,
		"step_label": STEP_LABELS.get(meta.step, ""),
		"status": meta.status,
		**progress,
	}

	if request.headers.get("HX-Request") == "true":
		return templates.TemplateResponse(
			request=request,
			name="filter_progress.html",
			context={
				"filter_status": status,
				"filter_step_filter": STEP_FILTER,
				"filter_status_ingesting": STATUS_INGESTING,
			},
		)

	return status


def _run_filter_task(dataset_id: str) -> None:
	from src.chunking.chunk_runner import load_chunks
	from src.pipeline import Pipeline

	meta = load_meta(dataset_id)
	if meta is None:
		return

	try:
		chunks = load_chunks(dataset_dir(dataset_id))
		filtered = Pipeline().filter_chunks(chunks, output_path=dataset_dir(dataset_id))
		meta.stage_counts["filter"] = len(filtered)
		meta.status = STATUS_SUCCESS
	except Exception as error:
		meta.status = STATUS_FAILED
		meta.error = str(error)
	finally:
		save_meta(meta)

