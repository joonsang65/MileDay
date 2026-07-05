# 회원가입, 로그인, 로그아웃, 사용자 정보 조회 API 제공
from fastapi import APIRouter

from schemas.auth_schemas import (
    LogInRequest,
    LogInResponse,
    LogOutResponse,
    SignUpRequest,
    SignUpResponse,
    UserStatusResponse,
)


router = APIRouter(prefix="/auth", tags=["auth"])


# 회원가입 API
@router.post(
    "/signup",
    response_model=SignUpResponse,
    summary="회원가입",
    description="이메일과 비밀번호를 기반으로 회원가입을 처리",
)
def signup(body: SignUpRequest):
    return {
        "success": True,
        "data": {
            "user_id": "uuid",
            "email": body.email,
        },
    }


# 로그인 API
@router.post(
    "/login",
    response_model=LogInResponse,
    summary="로그인",
    description=(
        "이메일과 비밀번호를 기반으로 로그인"
        "Supabase Auth에서 발급된 Access Token과 Refresh Token 반환"
    ),
)
def login(body: LogInRequest):
    return {
        "success": True,
        "data": {
            "access_token": "jwt_access_token",
            "refresh_token": "refresh_token",
            "token_type": "bearer",
            "user": {
                "id": "uuid",
                "email": body.email,
            },
        },
    }


# 로그아웃 API
@router.post(
    "/logout",
    response_model=LogOutResponse,
    summary="로그아웃",
    description="현재 사용자의 로그아웃 처리",
)
def logout():
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
def user():
    return {
        "success": True,
        "data": {
            "user_id": "uuid",
            "email": "user@example.com",
        },
    }
