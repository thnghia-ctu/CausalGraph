from fastapi import APIRouter, UploadFile, File, Form

router = APIRouter()


@router.post("/api/datasets")
async def create_dataset(
    data_name: str = Form(...),
    description: str = Form(""),
    data_file: UploadFile = File(...),
):
    ...