import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.frontend.pages.filter_page import router as filter_page
from app.frontend.pages.graph_visualize_page import router as graph_visualize_page
from app.frontend.pages.ingest_page import router as ingest_page
from app.frontend.pages.home import router as home_router
from app.backend.api.dataset import router as dataset_router
from app.backend.api.filter_config import router as filter_config_router
from app.backend.api.pipeline import router as pipeline_router


app = FastAPI(
    title="Personal Pipeline App",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "causalgraph-local-session-key"),
)

app.mount(
    "/static",
    StaticFiles(directory="app/frontend/static"),
    name="static",
)

app.include_router(filter_page)
app.include_router(graph_visualize_page)
app.include_router(ingest_page)
app.include_router(home_router)
app.include_router(dataset_router)
app.include_router(filter_config_router)
app.include_router(pipeline_router)