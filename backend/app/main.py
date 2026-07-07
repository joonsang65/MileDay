# M1 공통 진입점: 설정, 로깅, 미들웨어, 예외 핸들러, 라우터 등록
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    # backend/app 직접 실행 시 절대 import 경로 보정
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
from exceptions.base import MileDayBaseException
from exceptions.handlers import (
    http_exception_handler,
    mileday_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException

settings = get_settings()
configure_logging()

app = FastAPI(title=settings.app_name)

# 요청 문맥 미들웨어가 CORS보다 먼저 request_id 확보
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모든 실패 응답을 공통 ErrorResponse 형태로 변환
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
def health_db() -> dict[str, str]:
    # 외부 DB 연결 없이 환경 변수 구성 상태만 노출
    status = "configured" if settings.is_supabase_configured else "not_configured"
    return {"status": status}


# 기능별 라우터는 공통 미들웨어와 핸들러 등록 뒤 연결
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
