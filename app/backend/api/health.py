from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
def health():
    return {"status": "ok"}

@router.get("/api/health/html")
def health_html():
    return "<strong>Backend đang hoạt động.</strong>"