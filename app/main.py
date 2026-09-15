from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.backend.api.health import router as health_router


app = FastAPI(
    title="Personal Pipeline App",
)

app.include_router(health_router)

templates = Jinja2Templates(
    directory="app/frontend/templates"
)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )