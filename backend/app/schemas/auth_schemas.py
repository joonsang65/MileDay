from pydantic import BaseModel, EmailStr, Field


# 회원가입 요청 DTO
class SignUpRequest(BaseModel):
    # 이메일/비밀번호 회원가입 요청
    email: EmailStr
    password: str = Field(min_length=8)


class SignUpData(BaseModel):
    # 회원가입 후 반환할 사용자 식별 정보
    user_id: str
    email: EmailStr


# 회원가입 응답 DTO
class SignUpResponse(BaseModel):
    # 회원가입 성공 응답 envelope
    success: bool
    data: SignUpData


# 로그인 요청 DTO
class LogInRequest(BaseModel):
    # 이메일/비밀번호 로그인 요청
    email: EmailStr
    password: str = Field(min_length=8)


class LogInUser(BaseModel):
    # 로그인 응답에 포함할 사용자 정보
    id: str
    email: EmailStr


class LogInData(BaseModel):
    # Supabase Auth 세션 정보와 사용자 정보
    access_token: str
    refresh_token: str
    token_type: str
    user: LogInUser


# 로그인 응답 DTO
class LogInResponse(BaseModel):
    # 로그인 성공 응답 envelope
    success: bool
    data: LogInData


# 로그아웃 응답 DTO
class LogOutResponse(BaseModel):
    # 로그아웃 성공 응답 envelope
    success: bool
    message: str


class CurrentUserData(BaseModel):
    # JWT 검증 결과 기반 현재 사용자 정보
    user_id: str
    email: EmailStr


# 사용자 정보 조회 DTO
class UserStatusResponse(BaseModel):
    # 현재 사용자 조회 응답 envelope
    success: bool
    data: CurrentUserData
