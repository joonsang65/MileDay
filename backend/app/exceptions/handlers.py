import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.logging import mask_sensitive_data
from exceptions.base import MileDayBaseException
from schemas.common import ErrorCode


logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    # middleware 미통과 상황의 안전한 fallback
    return getattr(request.state, "request_id", "-")


def error_payload(
    *,
    request_id: str,
    code: ErrorCode | str,
    message: str,
    detail: object | None = None,
) -> dict:
    # frontend 공통 처리용 실패 응답 envelope
    return {
        "success": False,
        "error": {
            "code": str(code),
            "message": message,
            "detail": mask_sensitive_data(detail),
        },
        "request_id": request_id,
    }


async def mileday_exception_handler(
    request: Request, exc: MileDayBaseException
) -> JSONResponse:
    # 예상 가능한 도메인 오류는 warning 레벨
    logger.warning(
        "application error",
        extra={"error_code": str(exc.error_code), "status_code": exc.status_code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            request_id=_request_id(request),
            code=exc.error_code,
            message=exc.message,
            detail=exc.detail,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # FastAPI 기본 422 대신 API 명세의 400 기준 적용
    logger.warning("request validation failed", extra={"error_code": ErrorCode.BAD_REQUEST})
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_payload(
            request_id=_request_id(request),
            code=ErrorCode.BAD_REQUEST,
            message="Invalid request.",
            detail=exc.errors(),
        ),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    # Starlette/FastAPI 오류를 MileDay error_code 체계로 매핑
    code_by_status = {
        status.HTTP_400_BAD_REQUEST: ErrorCode.BAD_REQUEST,
        status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
        status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
    }
    error_code = code_by_status.get(exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR)
    logger.warning(
        "http error",
        extra={"error_code": str(error_code), "status_code": exc.status_code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(
            request_id=_request_id(request),
            code=error_code,
            message=str(exc.detail),
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 예측 불가 오류는 응답에 내부 정보 미노출, 로그에만 stack trace 기록
    logger.exception("unhandled server error")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload(
            request_id=_request_id(request),
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Internal server error.",
        ),
    )
