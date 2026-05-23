from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.dependencies.auth import CurrentUser, get_current_user
from app.services.database_service import (
    DatabaseError,
    InvalidDetectionStatusError,
    get_v2_dashboard_overview,
    list_v2_detections,
    list_v2_scan_events,
    update_v2_detection_status,
)

router = APIRouter()


class V2DetectionStatusUpdate(BaseModel):
    status: str


@router.get("/v2/dashboard/overview")
def v2_dashboard_overview(current_user: CurrentUser = Depends(get_current_user)):
    """Return V2 dashboard overview scoped to the authenticated user's workspace."""
    try:
        return get_v2_dashboard_overview(current_user.id)
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to load V2 overview")


@router.get("/v2/scan-events")
def v2_scan_events(
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return recent V2 scan events scoped to the authenticated user's workspace."""
    try:
        return list_v2_scan_events(
            user_id=current_user.id,
            limit=limit,
            status=status,
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to load V2 scan events")


@router.get("/v2/detections")
def v2_detections(
    limit: int = Query(default=50, ge=1, le=100),
    status: str | None = None,
    severity: str | None = None,
    repository_id: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Return safe V2 detections scoped to the authenticated user's workspace."""
    try:
        return list_v2_detections(
            user_id=current_user.id,
            filters={
                "limit": limit,
                "status": status,
                "severity": severity,
                "repository_id": repository_id,
            },
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to load V2 detections")


@router.patch("/v2/detections/{detection_id}/status")
def set_v2_detection_status(
    detection_id: str,
    body: V2DetectionStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update status for a workspace-owned V2 detection."""
    try:
        updated = update_v2_detection_status(
            user_id=current_user.id,
            detection_id=detection_id,
            status=body.status,
        )
    except InvalidDetectionStatusError:
        raise HTTPException(status_code=400, detail="Invalid detection status")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Failed to update V2 detection")

    if not updated:
        raise HTTPException(status_code=404, detail="V2 detection not found")

    return updated
