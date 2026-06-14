"""Mail service interface for digest delivery (PRD §7.6, §10.4)."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, HttpUrl, field_validator, model_validator

from services.notifications import NotificationKind


class DigestNotificationEntry(BaseModel):
    notification_id: UUID
    type: NotificationKind
    product_id: UUID | None
    product_title: str
    summary: str
    deep_link: HttpUrl
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def validate_created_at_tz_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value


class DigestEmail(BaseModel):
    to_email: str
    subject: str
    text_body: str
    html_body: str
    entries: list[DigestNotificationEntry]

    @field_validator("to_email")
    @classmethod
    def validate_to_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("to_email must contain @")
        local, _, domain = value.partition("@")
        if not local or not domain:
            raise ValueError("to_email must have non-empty local and domain parts")
        return value

    @model_validator(mode="after")
    def validate_non_empty_entries(self) -> DigestEmail:
        if not self.entries:
            raise ValueError("entries must not be empty")
        return self


class MailServiceError(Exception):
    """Base error for mail service failures."""


class MailService(Protocol):
    def send_digest(self, email: DigestEmail) -> None:
        ...


class NoOpMailService:
    """Production-safe default when RESEND_API_KEY is unset."""

    def __init__(self) -> None:
        self.sent: list[DigestEmail] = []

    def send_digest(self, email: DigestEmail) -> None:
        self.sent.append(email)

    def reset(self) -> None:
        self.sent.clear()
