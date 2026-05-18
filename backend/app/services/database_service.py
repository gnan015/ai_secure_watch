import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import settings


STORED_DETECTION_FIELDS = {
    "repo_full_name",
    "repo_owner",
    "repo_name",
    "branch",
    "commit_sha",
    "file_path",
    "line_number",
    "secret_type",
    "masked_value",
    "detection_method",
    "entropy_score",
    "severity",
    "confidence_score",
    "ai_reasoning",
    "ai_recommendation",
    "status",
    "pusher_name",
    "pusher_email",
}
SAFE_DETECTION_FIELDS = [
    "id",
    "repo_full_name",
    "repo_owner",
    "repo_name",
    "branch",
    "commit_sha",
    "file_path",
    "line_number",
    "secret_type",
    "masked_value",
    "detection_method",
    "entropy_score",
    "severity",
    "confidence_score",
    "ai_reasoning",
    "ai_recommendation",
    "status",
    "pusher_name",
    "pusher_email",
    "detected_at",
    "resolved_at",
]
ALLOWED_STATUSES = {"open", "resolved", "dismissed"}


class DatabaseError(Exception):
    """Raised when a Supabase query fails."""


class DetectionNotFoundError(Exception):
    """Raised when a detection row does not exist."""


class InvalidDetectionStatusError(Exception):
    """Raised when a dashboard status update is not allowed."""


def _validate_supabase_settings() -> None:
    """Make sure Supabase backend credentials are configured."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("Supabase URL or service role key is not configured")


def _get_supabase_rest_url() -> str:
    """Build the REST URL for the detections table."""
    base_url = settings.supabase_url.rstrip("/")

    if base_url.endswith("/rest/v1"):
        return f"{base_url}/detections"

    return f"{base_url}/rest/v1/detections"


def _send_supabase_rest_request(
    method: str,
    query_params: dict | None = None,
    payload: dict | None = None,
) -> list:
    """Send a Supabase REST request and return JSON rows."""
    try:
        _validate_supabase_settings()
    except ValueError as exc:
        raise DatabaseError("Supabase settings are missing") from exc

    url = _get_supabase_rest_url()
    if query_params:
        url = f"{url}?{urlencode(query_params)}"

    request_body = json.dumps(payload).encode("utf-8") if payload else None
    request = Request(
        url,
        data=request_body,
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method=method,
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise DatabaseError(type(exc).__name__) from exc

    if not response_body:
        return []

    try:
        return json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise DatabaseError("Invalid Supabase JSON response") from exc


def _safe_detection(row: dict) -> dict:
    """Return only fields that are safe for the future React dashboard."""
    safe_row = {field: row.get(field) for field in SAFE_DETECTION_FIELDS}
    safe_row.pop("raw_value", None)
    return safe_row


def _safe_detections(rows: list) -> list:
    """Remove any accidental raw secret fields from a list of rows."""
    return [_safe_detection(row) for row in rows]


def _insert_with_supabase_sdk(detection_data: dict) -> dict:
    """Insert using the official Supabase SDK when it is installed."""
    # The service role key can bypass database security rules. Keep it only on
    # the backend and never expose it to a browser or frontend dashboard.
    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    response = supabase.table("detections").insert(detection_data).execute()

    if response.data:
        return response.data[0]

    return {"stored": True}


def _insert_with_rest_api(detection_data: dict) -> dict:
    """Insert using Supabase REST API as a Windows ARM64-friendly fallback."""
    request_body = json.dumps(detection_data).encode("utf-8")
    request = Request(
        _get_supabase_rest_url(),
        data=request_body,
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method="POST",
    )

    with urlopen(request, timeout=30) as response:
        response_body = response.read().decode("utf-8")

    inserted_rows = json.loads(response_body)
    if inserted_rows:
        return inserted_rows[0]

    return {"stored": True}


def should_store_detection(ai_result: dict) -> bool:
    """Store only risky detections that Gemini marked as actionable."""
    risky_levels = {"CRITICAL", "HIGH", "MEDIUM"}
    risk_level = str(ai_result.get("risk_level", "")).upper()

    return bool(ai_result.get("is_risky")) and risk_level in risky_levels


def get_detections(
    status: str | None = None,
    severity: str | None = None,
    repo: str | None = None,
    limit: int = 100,
) -> list:
    """Return safe detection rows for the future React dashboard."""
    query_params = {
        "select": ",".join(SAFE_DETECTION_FIELDS),
        "order": "detected_at.desc",
        "limit": max(1, min(limit, 500)),
    }

    if status:
        query_params["status"] = f"eq.{status}"

    if severity:
        query_params["severity"] = f"eq.{severity.upper()}"

    if repo:
        query_params["repo_full_name"] = f"eq.{repo}"

    rows = _send_supabase_rest_request("GET", query_params=query_params)
    return _safe_detections(rows)


def get_recent_detections(limit: int = 10) -> list:
    """Return the latest safe detection rows."""
    return get_detections(limit=max(1, min(limit, 100)))


def _get_all_dashboard_detections(limit: int = 10000) -> list:
    """Fetch rows used for dashboard stats."""
    rows = _send_supabase_rest_request(
        "GET",
        query_params={
            "select": ",".join(SAFE_DETECTION_FIELDS),
            "limit": limit,
        },
    )
    return _safe_detections(rows)


def get_summary_stats() -> dict:
    """Return dashboard summary counts."""
    detections = _get_all_dashboard_detections()

    return {
        "total_detections": len(detections),
        "open_detections": sum(1 for row in detections if row.get("status") == "open"),
        "resolved_detections": sum(
            1 for row in detections if row.get("status") == "resolved"
        ),
        "dismissed_detections": sum(
            1 for row in detections if row.get("status") == "dismissed"
        ),
        "critical_count": sum(
            1 for row in detections if row.get("severity") == "CRITICAL"
        ),
        "high_count": sum(1 for row in detections if row.get("severity") == "HIGH"),
        "medium_count": sum(
            1 for row in detections if row.get("severity") == "MEDIUM"
        ),
        "low_count": sum(1 for row in detections if row.get("severity") == "LOW"),
    }


def get_severity_stats() -> list:
    """Return detection counts grouped by severity."""
    detections = _get_all_dashboard_detections()

    return [
        {
            "severity": severity,
            "count": sum(1 for row in detections if row.get("severity") == severity),
        }
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    ]


def get_secret_type_stats() -> list:
    """Return detection counts grouped by secret type."""
    detections = _get_all_dashboard_detections()
    counts = {}

    for row in detections:
        secret_type = row.get("secret_type") or "unknown"
        counts[secret_type] = counts.get(secret_type, 0) + 1

    return [
        {"secret_type": secret_type, "count": count}
        for secret_type, count in sorted(counts.items())
    ]


def get_trend_stats(days: int = 30) -> list:
    """Return detection counts by date for the last number of days."""
    days = max(1, min(days, 365))
    start_date = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    detections = _get_all_dashboard_detections()
    counts = {}

    for row in detections:
        detected_at = row.get("detected_at")
        if not detected_at:
            continue

        try:
            detected_date = datetime.fromisoformat(
                detected_at.replace("Z", "+00:00")
            ).date()
        except ValueError:
            continue

        if detected_date >= start_date:
            date_key = detected_date.isoformat()
            counts[date_key] = counts.get(date_key, 0) + 1

    return [
        {
            "date": (start_date + timedelta(days=offset)).isoformat(),
            "count": counts.get((start_date + timedelta(days=offset)).isoformat(), 0),
        }
        for offset in range(days)
    ]


def update_detection_status(detection_id: str, status: str) -> dict:
    """Update a detection status for dashboard workflows."""
    normalized_status = status.lower()
    if normalized_status not in ALLOWED_STATUSES:
        raise InvalidDetectionStatusError("Invalid detection status")

    payload = {
        "status": normalized_status,
        "resolved_at": (
            datetime.now(timezone.utc).isoformat()
            if normalized_status == "resolved"
            else None
        ),
    }
    rows = _send_supabase_rest_request(
        "PATCH",
        query_params={
            "id": f"eq.{detection_id}",
            "select": ",".join(SAFE_DETECTION_FIELDS),
        },
        payload=payload,
    )

    if not rows:
        raise DetectionNotFoundError("Detection not found")

    return _safe_detection(rows[0])


def insert_detection(detection_data: dict) -> dict:
    """Insert one detection row into Supabase without storing raw secrets."""
    try:
        _validate_supabase_settings()

        safe_detection_data = {
            key: value
            for key, value in detection_data.items()
            if key in STORED_DETECTION_FIELDS
        }

        # Raw secrets must never be stored. This extra pop is defensive in case
        # a future caller accidentally includes raw_value in detection_data.
        safe_detection_data.pop("raw_value", None)

        try:
            return _insert_with_supabase_sdk(safe_detection_data)
        except ImportError:
            return _insert_with_rest_api(safe_detection_data)
    except (HTTPError, URLError, ValueError, json.JSONDecodeError) as exc:
        print(f"Supabase insert failed safely: {type(exc).__name__}")
        return {"stored": False, "error": type(exc).__name__}
    except Exception as exc:
        print(f"Supabase insert failed safely: {type(exc).__name__}")
        return {"stored": False, "error": type(exc).__name__}
