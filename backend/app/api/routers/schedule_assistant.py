# AI 기반 일정 생성, 제안, 수정, reschedule API 제공
from fastapi import APIRouter

router = APIRouter(prefix = "/ai", tags=["ai"])