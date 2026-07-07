import logging
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from core.config import get_settings


# 요청 단위 로그 문맥 설정
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_context: ContextVar[str | None] = ContextVar("user_id", default=None)
path_context: ContextVar[str | None] = ContextVar("path", default=None)
duration_context: ContextVar[float | None] = ContextVar("duration_ms", default=None)

# 로그와 에러 detail에서 숨길 비공개 키
SENSITIVE_KEYS = {
    "password",
    "access_token",
    "refresh_token",
    "authorization",
    "external_access_token",
    "external_refresh_token",
    "token",
}


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # request_id 미존재 로그도 formatter 오류 없이 출력
        record.request_id = request_id_context.get() or "-"
        record.user_id = user_id_context.get() or "-"
        record.path = path_context.get() or "-"
        duration = duration_context.get()
        record.duration_ms = "-" if duration is None else f"{duration:.2f}"
        return True


def mask_email(value: str) -> str:
    # 사용자 식별 가능성 축소, 도메인은 디버깅 정보로 유지
    if "@" not in value:
        return value
    name, domain = value.split("@", 1)
    if not name:
        return f"***@{domain}"
    return f"{name[:2]}***@{domain}"


def mask_sensitive_data(value: Any) -> Any:
    # 중첩 dict/list 전체에서 민감 정보 마스킹
    if isinstance(value, dict):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            lower_key = key.lower()
            if lower_key == "email" and isinstance(item, str):
                masked[key] = mask_email(item)
            elif lower_key == "ai_prompt":
                # 긴 사용자 입력은 로그 저장 대신 존재 여부만 표시
                masked[key] = "[OMITTED]"
            elif lower_key in SENSITIVE_KEYS:
                masked[key] = "[MASKED]"
            else:
                masked[key] = mask_sensitive_data(item)
        return masked
    if isinstance(value, list):
        return [mask_sensitive_data(item) for item in value]
    return value


def configure_logging() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    log_dir: Path = settings.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # uvicorn 재로더와 테스트 재실행 시 handler 중복 방지
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s request_id=%(request_id)s "
        "user_id=%(user_id)s path=%(path)s duration_ms=%(duration_ms)s "
        "%(name)s - %(message)s"
    )

    context_filter = RequestContextFilter()

    # 개발 중 즉시 확인용 콘솔 로그
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)

    # 운영 추적용 일별 파일 로그
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / "mileday.log",
        when="midnight",
        interval=1,
        backupCount=settings.log_retention_days,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(context_filter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
