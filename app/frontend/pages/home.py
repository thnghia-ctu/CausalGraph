from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router= APIRouter()

template=Jinja2Templates(directory="app/frontend/templates")

@router.get("/")
def home(request: Request):
    return template.TemplateResponse(
        request=request,
        name="index.html",
    )