from fastapi import APIRouter
from ..db import engine

router = APIRouter()

@router.get("/healthz")
def healthz():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
