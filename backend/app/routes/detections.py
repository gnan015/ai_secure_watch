from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.database_service import (
    ALLOWED_STATUSES,
    DatabaseError,
    DetectionNotFoundError,
    InvalidDetectionStatusError,
    get_detections,
    get_recent_detections,
    get_secret_type_stats,
    get_severity_stats,
    get_summary_stats,
    get_trend_stats,
    update_detection_status,
)

router = APIRouter()


class DetectionStatusUpdate(BaseModel):
    status: str


def _handle_database_error() -> None:
    """Return a clean API error if Supabase is unavailable."""
    raise HTTPException(
        status_code=500,
        detail="Supabase query failed. Please try again later.",
    )


@router.get("/detections")
def list_detections(
    status: str | None = None,
    severity: str | None = None,
    repo: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Return safe detection rows for the future React dashboard."""
    if status and status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    try:
        return get_detections(
            status=status,
            severity=severity,
            repo=repo,
            limit=limit,
        )
    except DatabaseError:
        _handle_database_error()


@router.get("/detections/recent")
def list_recent_detections(limit: int = Query(default=10, ge=1, le=100)):
    """Return the most recent safe detections."""
    try:
        return get_recent_detections(limit=limit)
    except DatabaseError:
        _handle_database_error()


@router.get("/stats/summary")
def read_summary_stats():
    """Return dashboard summary counts."""
    try:
        return get_summary_stats()
    except DatabaseError:
        _handle_database_error()


@router.get("/stats/severity")
def read_severity_stats():
    """Return dashboard counts grouped by severity."""
    try:
        return get_severity_stats()
    except DatabaseError:
        _handle_database_error()


@router.get("/stats/secret-types")
def read_secret_type_stats():
    """Return dashboard counts grouped by secret type."""
    try:
        return get_secret_type_stats()
    except DatabaseError:
        _handle_database_error()


@router.get("/stats/trends")
def read_trend_stats():
    """Return daily detection counts from the last 30 days."""
    try:
        return get_trend_stats(days=30)
    except DatabaseError:
        _handle_database_error()


@router.patch("/detections/{detection_id}/status")
def change_detection_status(detection_id: str, body: DetectionStatusUpdate):
    """Update a detection status from the future React dashboard."""
    try:
        return update_detection_status(detection_id=detection_id, status=body.status)
    except InvalidDetectionStatusError:
        raise HTTPException(status_code=400, detail="Invalid status")
    except DetectionNotFoundError:
        raise HTTPException(status_code=404, detail="Detection not found")
    except DatabaseError:
        _handle_database_error()
