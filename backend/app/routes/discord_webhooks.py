from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies.auth import CurrentUser, get_current_user
from app.services.database_service import (
    DatabaseError,
    create_discord_webhook_for_user_workspace,
    delete_discord_webhook_for_user_workspace,
    get_discord_webhook_for_user_workspace,
    get_discord_webhooks_for_user_workspace,
    get_owned_workspace_for_user,
    update_discord_webhook_for_user_workspace,
)
from app.services.discord_webhook_service import (
    DiscordWebhookServiceError,
    decrypt_webhook_url,
    encrypt_webhook_url,
    mask_webhook_last4,
    send_test_webhook_message,
)

router = APIRouter()


class DiscordWebhookCreateRequest(BaseModel):
    name: str = Field(default="Default Discord Webhook", min_length=1, max_length=200)
    webhook_url: str = Field(..., min_length=1)
    enabled: bool = True


class DiscordWebhookUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    webhook_url: str | None = Field(default=None, min_length=1)
    enabled: bool | None = None


@router.get("/discord/webhooks")
def list_discord_webhooks(current_user: CurrentUser = Depends(get_current_user)):
    try:
        return get_discord_webhooks_for_user_workspace(current_user.id)
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to load Discord webhooks")


@router.post("/discord/webhooks")
def create_discord_webhook(
    body: DiscordWebhookCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        encrypted_url = encrypt_webhook_url(body.webhook_url)
        last4 = mask_webhook_last4(body.webhook_url)
        created = create_discord_webhook_for_user_workspace(
            user_id=current_user.id,
            name=body.name.strip(),
            webhook_url_ciphertext=encrypted_url,
            webhook_url_last4=last4,
            enabled=body.enabled,
        )
    except DiscordWebhookServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to create Discord webhook")

    if not created:
        raise HTTPException(status_code=404, detail="No owned workspace found")
    return created


@router.patch("/discord/webhooks/{webhook_id}")
def update_discord_webhook(
    webhook_id: str,
    body: DiscordWebhookUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    patch_data: dict = {}
    if body.name is not None:
        patch_data["name"] = body.name.strip()
    if body.enabled is not None:
        patch_data["enabled"] = body.enabled
    if body.webhook_url is not None:
        try:
            patch_data["webhook_url_ciphertext"] = encrypt_webhook_url(body.webhook_url)
            patch_data["webhook_url_last4"] = mask_webhook_last4(body.webhook_url)
        except DiscordWebhookServiceError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    try:
        updated = update_discord_webhook_for_user_workspace(
            user_id=current_user.id,
            webhook_id=webhook_id,
            patch_data=patch_data,
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to update Discord webhook")

    if not updated:
        raise HTTPException(status_code=404, detail="Discord webhook not found")
    return updated


@router.delete("/discord/webhooks/{webhook_id}")
def delete_discord_webhook(
    webhook_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        deleted = delete_discord_webhook_for_user_workspace(
            user_id=current_user.id,
            webhook_id=webhook_id,
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to delete Discord webhook")

    if not deleted:
        raise HTTPException(status_code=404, detail="Discord webhook not found")
    return {"status": "deleted", "id": webhook_id}


@router.post("/discord/webhooks/{webhook_id}/test")
def test_discord_webhook(
    webhook_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    try:
        webhook = get_discord_webhook_for_user_workspace(
            user_id=current_user.id,
            webhook_id=webhook_id,
            include_ciphertext=True,
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to load Discord webhook")

    if not webhook:
        raise HTTPException(status_code=404, detail="Discord webhook not found")

    try:
        webhook_url = decrypt_webhook_url(webhook["webhook_url_ciphertext"])
        workspace = get_owned_workspace_for_user(current_user.id)
        workspace_name = workspace.get("name") if workspace else None
        send_test_webhook_message(webhook_url, workspace_name=workspace_name)
    except DiscordWebhookServiceError as exc:
        try:
            update_discord_webhook_for_user_workspace(
                user_id=current_user.id,
                webhook_id=webhook_id,
                patch_data={
                    "last_tested_at": datetime.now(timezone.utc).isoformat(),
                    "last_error": str(exc),
                },
            )
        except DatabaseError:
            pass
        raise HTTPException(status_code=502, detail=str(exc))

    try:
        updated = update_discord_webhook_for_user_workspace(
            user_id=current_user.id,
            webhook_id=webhook_id,
            patch_data={
                "last_tested_at": datetime.now(timezone.utc).isoformat(),
                "last_error": None,
            },
        )
    except DatabaseError:
        updated = None

    return {
        "status": "sent",
        "webhook_id": webhook_id,
        "last_tested_at": updated.get("last_tested_at") if updated else None,
    }
