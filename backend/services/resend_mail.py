"""Resend-backed MailService for digest delivery (T3.6)."""

from __future__ import annotations

import resend

from core.settings import Settings
from services.mail import DigestEmail, MailServiceError


class ResendMailService:
    def __init__(self, settings: Settings) -> None:
        self._from_email = settings.resend_from_email
        resend.api_key = settings.resend_api_key

    def send_digest(self, email: DigestEmail) -> None:
        try:
            resend.Emails.send(
                {
                    "from": self._from_email,
                    "to": [str(email.to_email)],
                    "subject": email.subject,
                    "html": email.html_body,
                    "text": email.text_body,
                }
            )
        except Exception as exc:  # noqa: BLE001 — surface provider failures uniformly
            raise MailServiceError(str(exc)) from exc
