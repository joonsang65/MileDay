from pydantic import BaseModel, EmailStr

# 회원가입 요청 DTO
class SignUpRequest(BaseModel):
    email : EmailStr
    password : str

class SignUpData(BaseModel):
    user_id : str
    email : EmailStr

# 회원가입 응답 DTO
class SignUpResponse(BaseModel):
    success : bool
    data : SignUpData



# 로그인 요청 DTO
class LogInRequest(BaseModel):
    email : EmailStr
    password : str

class LogInUser(BaseModel):
    id : str
    email : EmailStr

class LogInData(BaseModel):
    access_token : str
    refresh_token : str
    token_type : str
    user : LogInUser

# 로그인 응답 DTO
class LogInResponse(BaseModel):
    success : bool
    data : LogInData

# 로그아웃 응답 DTO
class LogOutResponse(BaseModel):
    success : bool
    message : str

# 사용자 정보 조회 DTO
class UserStatusResponse(BaseModel):
    success : bool
    data : dict[str, str]
