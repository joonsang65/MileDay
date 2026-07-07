# 회원가입, 로그인, 로그아웃, 사용자 정보 조회 API 제공
from fastapi import APIRouter, Depends

from core.auth import get_bearer_token, get_current_user
from schemas.auth_schemas import (
    LogInRequest,
    LogInResponse,
    LogOutResponse,
    SignUpRequest,
    SignUpResponse,
    UserStatusResponse,
)
from services.auth_service import AuthService, AuthUser, get_auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


# 회원가입 API
@router.post(
    "/signup",
    response_model=SignUpResponse,
    summary="회원가입",
    description="이메일과 비밀번호를 기반으로 Supabase Auth 사용자를 생성",
)
def signup(
    body: SignUpRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    # Supabase Auth 회원 생성
    user = auth_service.signup(email=str(body.email), password=body.password)
    return {
        "success": True,
        "data": {
            "user_id": user.id,
            "email": user.email,
        },
    }


# 로그인 API
@router.post(
    "/login",
    response_model=LogInResponse,
    summary="로그인",
    description="이메일과 비밀번호를 검증하고 인증 토큰 반환",
)
def login(
    body: LogInRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    # Supabase Auth 세션 생성
    session = auth_service.login(email=str(body.email), password=body.password)
    return {
        "success": True,
        "data": {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": session.token_type,
            "user": {
                "id": session.user.id,
                "email": session.user.email,
            },
        },
    }


# 로그아웃 API
@router.post(
    "/logout",
    response_model=LogOutResponse,
    summary="로그아웃",
    description="현재 접근 토큰 검증 후 로그아웃 처리",
)
def logout(
    access_token: str = Depends(get_bearer_token),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    # 현재 접근 토큰 검증 후 로그아웃 처리
    auth_service.logout(access_token)
    return {
        "success": True,
        "message": "로그아웃되었습니다.",
    }


# 현재 사용자 조회 API
@router.get(
    "/me",
    response_model=UserStatusResponse,
    summary="현재 사용자 조회",
    description="현재 JWT를 기준으로 로그인한 사용자 정보 조회",
)
def user(current_user: AuthUser = Depends(get_current_user)) -> dict:
    # JWT 기준 현재 사용자 정보 반환
    return {
        "success": True,
        "data": {
            "user_id": current_user.id,
            "email": current_user.email,
        },
    }
