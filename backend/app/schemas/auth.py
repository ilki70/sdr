from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tenant_id: str = Field(min_length=3, max_length=120)


class LoginResponse(BaseModel):
    user_id: str
    tenant_id: str
    role: str
    email: EmailStr
    full_name: str
    message: str


class MessageResponse(BaseModel):
    message: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    tenant_id: str = Field(min_length=3, max_length=120)
    role: str = Field(default="operator", max_length=16)


class SessionResponse(BaseModel):
    user_id: str
    tenant_id: str
    role: str
    request_id: str


class AdminResetUserPasswordRequest(BaseModel):
    tenant_id: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = Field(default=None, max_length=16)


class AdminResetUserPasswordResponse(BaseModel):
    tenant_id: str
    email: EmailStr
    user_id: str
    role: str
    status: str


class GoogleLoginRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    tenant_id: str = Field(min_length=3, max_length=120)
    role: str | None = Field(default=None, max_length=16)
