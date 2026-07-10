from __future__ import annotations

from fastapi import Depends, Header

from exceptions.auth import AuthInvalidTokenError
from exceptions.common import UnauthorizedError
from services.auth_service import AuthService, AuthUser, get_auth_service


def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    # 인증 헤더에서 bearer 토큰 추출
    if not authorization:
        raise UnauthorizedError()

    # 잘못된 헤더가 통과하지 않도록 정확히 "Bearer <token>" 형식만 허용한다.
    parts = authorization.strip().split()
    if len(parts) != 2:
        raise AuthInvalidTokenError()

    scheme, token = parts
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthInvalidTokenError()

    return token


def get_current_user(
    access_token: str = Depends(get_bearer_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthUser:
    # Supabase Auth JWT 검증 후 현재 사용자 반환
    return auth_service.get_user(access_token)


def require_current_user_id(current_user: AuthUser = Depends(get_current_user)) -> str:
    # 서비스와 저장소 계층에서 사용할 현재 user_id
    return current_user.id
