# API 엔트리포인트, 라우터 등록, 서버 상태 확인을 담당
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from api.routers.auth import router as auth_router
from api.routers.calender import router as calender_router
from api.routers.external_calender import router as external_calender_router
from api.routers.goals import router as goals_router
from api.routers.milestones import router as milestones_router
from api.routers.schedule_assistant import router as schedule_assistant_router
from api.routers.settings import router as settings_router


app = FastAPI(title="MileDay")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "MileDay API"}


@app.get("/health", summary="서버 상태 확인")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", summary="DB 상태 확인")
def health_db() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(goals_router)
app.include_router(milestones_router)
app.include_router(calender_router)
app.include_router(settings_router)
app.include_router(external_calender_router)
app.include_router(schedule_assistant_router)

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
