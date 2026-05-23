from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies.auth import CurrentUser, get_current_user
from app.services.database_service import (
    DatabaseError,
    get_repositories_for_user_workspace,
    update_repository_monitoring,
)

router = APIRouter()


class RepositoryMonitoringUpdate(BaseModel):
    monitoring_enabled: bool


@router.get("/repositories")
def list_repositories(current_user: CurrentUser = Depends(get_current_user)):
    """Return repositories for the authenticated user's workspace."""
    try:
        return get_repositories_for_user_workspace(current_user.id)
    except DatabaseError:
        raise HTTPException(
            status_code=500,
            detail="Failed to load repositories",
        )


@router.patch("/repositories/{repository_id}/monitoring")
def set_repository_monitoring(
    repository_id: str,
    body: RepositoryMonitoringUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update monitoring_enabled for a workspace-owned repository."""
    try:
        updated = update_repository_monitoring(
            user_id=current_user.id,
            repository_id=repository_id,
            monitoring_enabled=body.monitoring_enabled,
        )
    except DatabaseError:
        raise HTTPException(
            status_code=500,
            detail="Failed to update repository monitoring",
        )

    if not updated:
        raise HTTPException(status_code=404, detail="Repository not found")

    return updated
