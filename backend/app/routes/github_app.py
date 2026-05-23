from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies.auth import CurrentUser, get_current_user
from app.services.database_service import (
    DatabaseError,
    get_github_installation_for_workspace,
    get_owned_workspace_for_user,
    upsert_repositories_for_installation,
    upsert_github_installation,
)
from app.services.github_app_service import (
    GitHubAppServiceError,
    get_installation,
    list_installation_repositories,
)

router = APIRouter()


class InstallationSaveRequest(BaseModel):
    installation_id: int = Field(..., gt=0)


@router.post("/github/installations")
def save_github_installation(
    body: InstallationSaveRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Save a GitHub App installation_id to the current user's owned workspace."""
    try:
        workspace = get_owned_workspace_for_user(current_user.id)
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Workspace lookup failed")

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="No owned workspace found for authenticated user",
        )

    try:
        installation = get_installation(body.installation_id)
    except GitHubAppServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    account = installation.get("account") or {}
    saved_payload = {
        "workspace_id": workspace["id"],
        "installation_id": installation.get("id", body.installation_id),
        "account_login": account.get("login") or "unknown",
        "account_type": account.get("type"),
        "account_id": account.get("id"),
        "app_slug": installation.get("app_slug"),
        "installed_by_user_id": current_user.id,
    }

    try:
        saved = upsert_github_installation(saved_payload)
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to save installation")

    return {
        "status": "saved",
        "workspace_id": saved.get("workspace_id"),
        "installation_id": saved.get("installation_id"),
        "account_login": saved.get("account_login"),
        "account_type": saved.get("account_type"),
        "account_id": saved.get("account_id"),
        "app_slug": saved.get("app_slug"),
    }


@router.post("/github/installations/{installation_id}/sync-repositories")
def sync_installation_repositories(
    installation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Sync repositories for a saved GitHub App installation."""
    if installation_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid installation_id")

    try:
        workspace = get_owned_workspace_for_user(current_user.id)
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Workspace lookup failed")

    if not workspace:
        raise HTTPException(
            status_code=404,
            detail="No owned workspace found for authenticated user",
        )

    try:
        installation_row = get_github_installation_for_workspace(
            workspace_id=workspace["id"],
            installation_id=installation_id,
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Installation lookup failed")

    if not installation_row:
        raise HTTPException(
            status_code=404,
            detail="Installation not found for authenticated workspace",
        )

    try:
        repositories = list_installation_repositories(installation_id)
    except GitHubAppServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    try:
        saved_rows = upsert_repositories_for_installation(
            workspace_id=workspace["id"],
            github_installation_db_id=installation_row["id"],
            repositories=repositories,
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Repository sync failed")

    summaries = [
        {
            "github_repo_id": row.get("github_repo_id"),
            "full_name": row.get("full_name"),
            "private": row.get("private"),
            "monitoring_enabled": row.get("monitoring_enabled"),
        }
        for row in saved_rows
    ]

    return {
        "status": "synced",
        "installation_id": installation_id,
        "workspace_id": workspace["id"],
        "synced_count": len(saved_rows),
        "repositories": summaries,
    }
