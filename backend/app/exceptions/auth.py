from fastapi import status

from exceptions.base import MileDayBaseException
from schemas.common import ErrorCode


class AuthInvalidCredentialsError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
            message="Invalid email or password.",
            detail=detail,
        )


class AuthInvalidTokenError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_INVALID_TOKEN,
            message="Invalid access token.",
            detail=detail,
        )


class AuthTokenExpiredError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Access token has expired.",
            detail=detail,
        )


class AuthUserNotFoundError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.AUTH_USER_NOT_FOUND,
            message="User was not found.",
            detail=detail,
        )
