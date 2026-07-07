from fastapi import status

from exceptions.base import MileDayBaseException
from schemas.common import ErrorCode


class SettingsNotFoundError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SETTINGS_NOT_FOUND,
            message="Settings were not found.",
            detail=detail,
        )


class SettingsUpdateFailedError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.SETTINGS_UPDATE_FAILED,
            message="Failed to update settings.",
            detail=detail,
        )


class SettingsInvalidValueError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.SETTINGS_INVALID_VALUE,
            message="Invalid settings value.",
            detail=detail,
        )
