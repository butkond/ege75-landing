from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import re


class LeadRequest(BaseModel):
    name: str
    student_class: str
    goal: Optional[str] = None
    contact: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя не может быть пустым")
        if len(v) > 100:
            raise ValueError("Имя слишком длинное")
        if len(v) < 2:
            raise ValueError("Имя слишком короткое")
        return v

    @field_validator("student_class")
    @classmethod
    def validate_class(cls, v: str) -> str:
        allowed = {"10", "11", "gap"}
        if v not in allowed:
            raise ValueError(f"Класс должен быть одним из: {', '.join(allowed)}")
        return v

    @field_validator("contact")
    @classmethod
    def validate_contact(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Контакт не может быть пустым")
        if len(v) > 100:
            raise ValueError("Контакт слишком длинный")

        # Telegram username или телефон
        is_telegram = bool(re.match(r"^@[a-zA-Z0-9_]{4,32}$", v))
        is_phone = bool(re.match(r"^\+?[0-9\s\-$$]{7,20}$", v))

        if not is_telegram and not is_phone:
            raise ValueError("Укажите Telegram (@username) или телефон (+7...)")
        return v

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) > 300:
                raise ValueError("Цель слишком длинная")
            if not v:
                return None
        return v


class LeadResponse(BaseModel):
    success: bool
    message: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
