from functools import lru_cache
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


def check_supabase_db_health() -> dict[str, Any]:
    # 실제 Supabase REST DB endpoint까지 도달 가능한지 최소 조회로 확인한다.
    response = (
        get_supabase_admin_client()
        .table("goals")
        .select("id,title,deadline,is_recurring,recurrence_type,color")
        .limit(1)
        .execute()
    )
    return {"row_count": len(response.data or [])}
