from pydantic import BaseModel, EmailStr
from typing import Optional
from enums.providerenum import ProviderEnum

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class OAuthLoginSchema(BaseModel):
    provider: ProviderEnum
    provider_id: str
    email: EmailStr
    name: Optional[str] = None
    profile_picture: Optional[str] = None

class OAuthRegisterSchema(BaseModel):
    provider: ProviderEnum
    provider_id: str
    email: EmailStr
    name: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    profile_picture: Optional[str] = None