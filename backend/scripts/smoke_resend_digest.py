"""Manual live Resend digest smoke. NOT run in CI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from core.settings import effective_app_base_url, get_settings  # noqa: E402
from services.digest_templates import build_digest_email  # noqa: E402
from services.factory import get_mail_service  # noqa: E402
from services.mail import DigestNotificationEntry, NoOpMailService  # noqa: E402
from services.notifications import NotificationKind  # noqa: E402


def _sample_entry() -> DigestNotificationEntry:
    product_id = uuid4()
    return DigestNotificationEntry(
        notification_id=uuid4(),
        type=NotificationKind.PRICE_DROP,
        product_id=product_id,
        product_title="Smoke Test Product",
        summary="Smoke Test Product dropped from $100.00 to $80.00.",
        deep_link=f"{effective_app_base_url(get_settings()).rstrip('/')}/products/{product_id}",
        created_at=datetime.now(UTC),
    )


def main() -> int:
    if sys.version_info < (3, 12):
        print(
            "Python 3.12+ is required for the backend. "
            f"Current interpreter: {sys.version.split()[0]}",
            file=sys.stderr,
        )
        return 1

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Send a real Resend email (requires RESEND_API_KEY). Never use in CI.",
    )
    parser.add_argument(
        "--to",
        default="rutvik@ualberta.ca",
        help="Recipient for --live smoke (Resend sandbox delivers to account owner only).",
    )
    args = parser.parse_args()

    if os.environ.get("CI", "").lower() in {"1", "true", "yes"} and args.live:
        print("Refusing --live Resend smoke in CI.", file=sys.stderr)
        return 1

    settings = get_settings()
    entry = _sample_entry()
    digest = build_digest_email(to_email=args.to, entries=[entry])

    if args.live:
        if not settings.resend_api_key.strip():
            print("RESEND_API_KEY is required for --live smoke.", file=sys.stderr)
            return 1
        mail = get_mail_service(settings)
        mail.send_digest(digest)
        mode = "live"
        provider = "resend"
    else:
        mail = NoOpMailService()
        mail.send_digest(digest)
        mode = "dry_run"
        provider = "noop"

    result = {
        "mode": mode,
        "mail_provider": provider,
        "to_email": args.to,
        "subject": digest.subject,
        "entries": len(digest.entries),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
