import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    # backend/app를 직접 실행할 때도 로컬 import가 동작하도록 경로를 보정한다.
    sys.path.insert(0, str(APP_DIR))

from api.routers.auth import router as auth_router
from api.routers.calender import router as calender_router
from api.routers.external_calender import router as external_calender_router
from api.routers.goals import router as goals_router
from api.routers.milestones import router as milestones_router
from api.routers.schedule_assistant import router as schedule_assistant_router
from api.routers.settings import router as settings_router
from core.config import get_settings
from core.logging import configure_logging
from core.middleware import RequestContextMiddleware
from core.supabase import check_supabase_db_health
from exceptions.base import MileDayBaseException
from exceptions.handlers import (
    http_exception_handler,
    mileday_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name)

# 요청 문맥 미들웨어가 CORS보다 먼저 request_id를 기록한다.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(MileDayBaseException, mileday_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "MileDay API"}


@app.get("/health", summary="서버 상태 확인")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", summary="DB 상태 확인")
def health_db() -> dict[str, str | int]:
    try:
        result = check_supabase_db_health()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unavailable",
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        ) from exc
    return {"status": "ok", **result}


app.include_router(auth_router)
app.include_router(goals_router)
app.include_router(milestones_router)
app.include_router(calender_router)
app.include_router(settings_router)
app.include_router(external_calender_router)
app.include_router(schedule_assistant_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.env == "development",
    )
