from fastapi import status

from exceptions.base import MileDayBaseException
from schemas.common import ErrorCode


class BadRequestError(MileDayBaseException):
    def __init__(self, message: str = "유효하지 않은 요청", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message=message,
            detail=detail,
        )


class UnauthorizedError(MileDayBaseException):
    def __init__(self, message: str = "인증 필요", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message=message,
            detail=detail,
        )


class NotFoundError(MileDayBaseException):
    def __init__(self, message: str = "리소스를 찾을 수 없습니다.", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            detail=detail,
        )


class ConflictError(MileDayBaseException):
    def __init__(self, message: str = "리소스 충돌이 발생했습니다.", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=message,
            detail=detail,
        )


class ExternalServiceError(MileDayBaseException):
    def __init__(self, message: str = "외부 서비스 요청 실패", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=message,
            detail=detail,
        )


class SupabaseUnavailableError(MileDayBaseException):
    def __init__(self, message: str = "Supabase 요청에 실패했습니다.", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.SUPABASE_UNAVAILABLE,
            message=message,
            detail=detail,
        )
