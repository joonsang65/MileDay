from fastapi import status

from exceptions.base import MileDayBaseException
from schemas.common import ErrorCode


class GoalNotFoundError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.GOAL_NOT_FOUND,
            message="Goal was not found.",
            detail=detail,
        )


class GoalCreateFailedError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.GOAL_CREATE_FAILED,
            message="Failed to create goal.",
            detail=detail,
        )


class GoalUpdateFailedError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.GOAL_UPDATE_FAILED,
            message="Failed to update goal.",
            detail=detail,
        )


class GoalDeleteFailedError(MileDayBaseException):
    def __init__(self, detail: object | None = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.GOAL_DELETE_FAILED,
            message="Failed to delete goal.",
            detail=detail,
        )
