from typing import Any

from schemas.common import ErrorCode


class MileDayBaseException(Exception):
    # 서비스 계층 오류를 HTTP 응답 정보와 함께 운반
    def __init__(
        self,
        *,
        status_code: int,
        error_code: ErrorCode | str,
        message: str,
        detail: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.detail = detail
        super().__init__(message)
