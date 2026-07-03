# 외부 캘린더 연동, 동기화, 상태 확인 API 제공
from fastapi import APIRouter

router = APIRouter(prefix = "/external-calenders", tags=["external-calenders"])