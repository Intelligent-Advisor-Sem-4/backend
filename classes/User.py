import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, validator, field_validator
from sqlalchemy import DateTime

from models.models import Gender


class User(BaseModel):
    username: str
    password: str
    user_id: str
    access_level: str

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    username: str
    token: str
    role: str
    email: EmailStr
    user_id: str
    name: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    username: str
    user_id: str
    access_level: str

    class Config:
        from_attributes = True


class UpdatePassword(BaseModel):
    password: str

    class Config:
        from_attributes = True


class UserRegistration(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str
    birthday: datetime
    gender: Gender
    avatar: Optional[str] = None

    @field_validator('username')
    def username_must_be_valid(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v

    @field_validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

    @field_validator('birthday')
    def validate_age(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 13:
            raise ValueError('You must be at least 13 years old to register')
        if v.year < 1900:
            raise ValueError('Birth year must be after 1900')
        return v


class RegistrationResponse(BaseModel):
    message: str
    user_id: str
