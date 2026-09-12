from pydantic import BaseModel, EmailStr, Field, field_validator

from app.validators.password import validate_password_strength


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)


class ProfileOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    is_verified: bool
    plan_name: str = "FREE"
    subscription_status: str = "ACTIVE"


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)
