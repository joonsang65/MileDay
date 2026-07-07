from functools import lru_cache

from supabase import Client, create_client

from core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    # 사용자 권한/RLS 기준 일반 Supabase client
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("Supabase URL and anon key are required.")
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache
def get_supabase_admin_client() -> Client:
    # 서버 전용 작업용 client, service role key 필수
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase URL and service role key are required.")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
