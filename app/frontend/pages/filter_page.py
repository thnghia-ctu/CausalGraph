from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
template = Jinja2Templates(directory="app/frontend/templates")

@router.get("/filter")
def filter_page(request: Request):
    selected_data_id = request.session.get("data_id")
    selected_dataset_name = request.session.get("data_name")
    return template.TemplateResponse(
        request=request,
        name="filter_page.html",
        context={
            "selected_data_id": selected_data_id,
            "selected_dataset_name": selected_dataset_name,
        },
    )