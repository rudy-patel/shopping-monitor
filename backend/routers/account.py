"""Account lifecycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from core.auth import CurrentUser, get_current_user
from core.settings import Settings, get_settings
from services.account_service import AccountDeleteError, AccountNotFoundError, AccountProtectedError, delete_account

router = APIRouter(prefix="/api", tags=["account"])


@router.delete("/account", status_code=204)
async def delete_account_endpoint(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Response:
    if settings.auth_bypass_enabled:
        raise HTTPException(
            status_code=403,
            detail="Account deletion is disabled in auth bypass mode",
        )

    try:
        delete_account(user.user_id, email=user.email)
    except AccountProtectedError as exc:
        raise HTTPException(status_code=403, detail="Cannot delete protected account") from exc
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Account not found") from exc
    except AccountDeleteError as exc:
        raise HTTPException(status_code=502, detail="Could not delete account") from exc

    return Response(status_code=204)
