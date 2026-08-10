"""Identity service request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from worldview.schemas import OrmModel


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)
    locale: str = Field(default="en", max_length=10)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=16)


class MfaEnrollOut(BaseModel):
    secret: str
    otpauth_url: str
    verified: bool = False


class MfaVerifyIn(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class MfaVerifyOut(BaseModel):
    verified: bool


class ConsentIn(BaseModel):
    policy_id: str = Field(min_length=1, max_length=80)
    accepted: bool = True


class ConsentOut(OrmModel):
    policy_id: str
    accepted_at: datetime


class UserOut(OrmModel):
    id: str
    email: EmailStr
    display_name: str
    locale: str
    is_verified: bool


class SessionOut(OrmModel):
    id: str
    device_id: str
    created_at: str


class GdprExportOut(BaseModel):
    export_id: str
    status: str
    data: dict


class GdprDeleteOut(BaseModel):
    job_id: str
    status: str
