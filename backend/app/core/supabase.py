from collections.abc import Callable
from functools import lru_cache
import time
from typing import Any

from supabase import Client, create_client

from core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    # Supabase Auth 호출에 사용하는 일반 client다.
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("Supabase URL and anon key are required.")
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache
def get_supabase_admin_client() -> Client:
    # 서버 내부 DB 작업에 사용하는 service role client다.
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase URL and service role key are required.")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def reset_supabase_admin_client() -> None:
    get_supabase_admin_client.cache_clear()


def reset_supabase_client() -> None:
    get_supabase_client.cache_clear()


def execute_supabase_read(operation: Callable[[], Any], *, attempts: int = 3) -> Any:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as error:
            last_error = error
            if attempt >= attempts or not is_retryable_supabase_error(error):
                raise
            reset_supabase_admin_client()
            time.sleep(0.1 if attempt == 1 else 0.3)
    if last_error:
        raise last_error
    raise RuntimeError("Supabase read operation did not run.")


def is_retryable_supabase_error(error: Exception) -> bool:
    error_name = error.__class__.__name__
    error_text = str(error)
    if error_name in {
        "APIError",
        "RemoteProtocolError",
        "ConnectError",
        "ReadError",
        "WriteError",
        "ConnectTimeout",
        "ReadTimeout",
        "WriteTimeout",
        "PoolTimeout",
        "TimeoutException",
        "NetworkError",
    }:
        return True

    status_value = getattr(error, "status", None) or getattr(error, "status_code", None)
    try:
        return int(status_value) in {500, 502, 503, 504}
    except (TypeError, ValueError):
        return any(
            marker in error_text
            for marker in (
                "RemoteProtocolError",
                "Server disconnected",
                "server disconnected",
                "502",
                "503",
                "504",
                "timeout",
                "Timeout",
            )
        )


def check_supabase_db_health() -> dict[str, Any]:
    # 실제 Supabase REST DB endpoint까지 도달 가능한지 최소 조회로 확인한다.
    response = (
        get_supabase_admin_client()
        .table("goals")
        .select("id,title,deadline,is_completed,is_recurring,recurrence_type,color")
        .limit(1)
        .execute()
    )
    return {"row_count": len(response.data or [])}
