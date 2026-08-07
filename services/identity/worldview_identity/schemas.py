"""Identity service request/response schemas."""

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
    token_type: str = "bearer"
    user_id: str


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
