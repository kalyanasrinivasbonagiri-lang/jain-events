from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class EventCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    date: datetime
    venue: str = Field(min_length=2, max_length=200)
    totalSeats: int = Field(gt=0, le=100000)

    @field_validator("date")
    @classmethod
    def date_to_utc(cls, value: datetime) -> datetime:
        return normalize_datetime(value)


class EventUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, min_length=5, max_length=2000)
    date: datetime | None = None
    venue: str | None = Field(default=None, min_length=2, max_length=200)
    totalSeats: int | None = Field(default=None, gt=0, le=100000)

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self

    @field_validator("date")
    @classmethod
    def date_to_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_datetime(value) if value else None


class StudentSignup(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    studentName: str = Field(min_length=2, max_length=100)
    email: EmailStr
    usn: str = Field(min_length=4, max_length=30, pattern=r"^[A-Za-z0-9/-]+$")
    branch: str = Field(min_length=2, max_length=80)
    year: int = Field(ge=1, le=4)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("usn")
    @classmethod
    def normalize_usn(cls, value: str) -> str:
        return value.upper()


class StudentLogin(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class AdminLogin(BaseModel):
    password: str = Field(min_length=1, max_length=256)


def mongo_json(document: dict[str, Any]) -> dict[str, Any]:
    """Convert MongoDB IDs and datetimes into JSON-compatible values."""
    result = dict(document)
    if "_id" in result:
        result["_id"] = str(result["_id"])
    if "eventId" in result:
        result["eventId"] = str(result["eventId"])
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [mongo_json(item) if isinstance(item, dict) else item for item in value]
        elif isinstance(value, dict):
            result[key] = mongo_json(value)
    return result
