from fastapi import status

from exceptions.base import MileDayBaseException
from schemas.common import ErrorCode


class MilestoneNotFoundError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.MILESTONE_NOT_FOUND,
            message="Milestone was not found.",
            detail=detail,
        )


class MilestoneCreateFailedError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.MILESTONE_CREATE_FAILED,
            message="Failed to create milestone.",
            detail=detail,
        )


class MilestoneUpdateFailedError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.MILESTONE_UPDATE_FAILED,
            message="Failed to update milestone.",
            detail=detail,
        )


class MilestoneDeleteFailedError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.MILESTONE_DELETE_FAILED,
            message="Failed to delete milestone.",
            detail=detail,
        )


class MilestoneInvalidScheduledDateError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.MILESTONE_INVALID_SCHEDULED_DATE,
            message="Invalid milestone scheduled date.",
            detail=detail,
        )
