from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    full_name: str = Field(default="", max_length=255)


class BootstrapRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    full_name: str = Field(default="", max_length=255)
    workspace_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPairResponse(AccessTokenResponse):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool

    model_config = {"from_attributes": True}
