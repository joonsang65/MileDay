from fastapi import status

from exceptions.base import MileDayBaseException
from schemas.common import ErrorCode


class AuthInvalidCredentialsError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="이메일 또는 비밀번호가 올바르지 않습니다.",
            detail=detail,
        )


class AuthInvalidTokenError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_INVALID_TOKEN,
            message="인증 토큰이 유효하지 않습니다.",
            detail=detail,
        )


class AuthTokenExpiredError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="인증 토큰이 만료되었습니다.",
            detail=detail,
        )


class AuthUserNotFoundError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.AUTH_USER_NOT_FOUND,
            message="사용자 정보를 찾을 수 없습니다.",
            detail=detail,
        )


class AuthLogoutFailedError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.AUTH_LOGOUT_FAILED,
            message="로그아웃 처리에 실패했습니다.",
            detail=detail,
        )
