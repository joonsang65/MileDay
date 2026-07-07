import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import duration_context, path_context, request_id_context


logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 클라이언트 request_id 우선 사용, 없으면 서버 추적용 ID 생성
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        request.state.request_id = request_id

        # 같은 요청 안의 로그가 동일한 문맥 값 공유
        request_token = request_id_context.set(request_id)
        path_token = path_context.set(request.url.path)
        duration_token = duration_context.set(None)
        start = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            duration_context.set(duration_ms)
            # 프론트엔드와 서버 로그 연결용 응답 헤더
            response.headers["X-Request-ID"] = request_id
            logger.debug(
                "request completed",
                extra={
                    "method": request.method,
                    "status_code": response.status_code,
                },
            )
            return response
        finally:
            # 다음 요청으로 contextvar 값 전파 방지
            request_id_context.reset(request_token)
            path_context.reset(path_token)
            duration_context.reset(duration_token)
