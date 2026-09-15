from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.backend.api.health import router as health_router
from app.frontend.pages.home import router as home_router
from app.backend.api.dataset import router as dataset_router


app = FastAPI(
    title="Personal Pipeline App",
)

app.mount(
    "/static",
    StaticFiles(directory="app/frontend/static"),
    name="static",
)

app.include_router(health_router)
app.include_router(home_router)
app.include_router(dataset_router)