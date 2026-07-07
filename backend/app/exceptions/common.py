from fastapi import status

from exceptions.base import MileDayBaseException
from schemas.common import ErrorCode


class BadRequestError(MileDayBaseException):
    def __init__(self, message: str = "Invalid request.", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.BAD_REQUEST,
            message=message,
            detail=detail,
        )


class UnauthorizedError(MileDayBaseException):
    def __init__(self, message: str = "Authentication is required.", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message=message,
            detail=detail,
        )


class NotFoundError(MileDayBaseException):
    def __init__(self, message: str = "Resource was not found.", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            detail=detail,
        )


class ConflictError(MileDayBaseException):
    def __init__(self, message: str = "Resource conflict occurred.", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message=message,
            detail=detail,
        )


class ExternalServiceError(MileDayBaseException):
    def __init__(self, message: str = "External service request failed.", detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=message,
            detail=detail,
        )
