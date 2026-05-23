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
V2_ALLOWED_DETECTION_STATUSES = {"open", "ignored", "resolved", "false_positive"}
V2_DETECTION_SAFE_FIELDS = [
    "id",
    "repository_id",
    "scan_event_id",
    "repo_full_name",
    "branch",
    "commit_sha",
    "file_path",
    "line_number",
    "secret_type",
    "masked_value",
    "detection_method",
    "severity",
    "confidence_score",
    "ai_reasoning",
    "ai_recommendation",
    "status",
    "detected_at",
    "created_at",
]
V2_DETECTION_FIELDS = {
    "workspace_id",
    "repository_id",
    "scan_event_id",
    "repo_full_name",
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
}
V2_SCAN_EVENT_SAFE_FIELDS = [
    "id",
    "repository_id",
    "repo_full_name",
    "branch",
    "commit_sha",
    "status",
    "error_message",
    "started_at",
    "completed_at",
    "created_at",
]


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


def _get_supabase_table_url(table_name: str) -> str:
    """Build the REST URL for any Supabase table."""
    base_url = settings.supabase_url.rstrip("/")

    if base_url.endswith("/rest/v1"):
        return f"{base_url}/{table_name}"

    return f"{base_url}/rest/v1/{table_name}"


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


def _send_supabase_table_request(
    table_name: str,
    method: str,
    query_params: dict | None = None,
    payload: dict | list | None = None,
    prefer: str = "return=representation",
) -> list:
    """Send a Supabase REST request to a specific table and return rows."""
    try:
        _validate_supabase_settings()
    except ValueError as exc:
        raise DatabaseError("Supabase settings are missing") from exc

    url = _get_supabase_table_url(table_name)
    if query_params:
        url = f"{url}?{urlencode(query_params)}"

    request_body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=request_body,
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
            "Prefer": prefer,
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


def get_owned_workspace_for_user(user_id: str) -> dict | None:
    """Return one workspace owned by the given user."""
    rows = _send_supabase_table_request(
        "workspaces",
        "GET",
        query_params={
            "select": "id,owner_user_id,name,created_at",
            "owner_user_id": f"eq.{user_id}",
            "order": "created_at.asc",
            "limit": 1,
        },
    )
    if not rows:
        return None
    return rows[0]


def upsert_github_installation(installation_data: dict) -> dict:
    """Upsert a github_installations row keyed by installation_id."""
    rows = _send_supabase_table_request(
        "github_installations",
        "POST",
        query_params={"on_conflict": "installation_id"},
        payload=installation_data,
        prefer="resolution=merge-duplicates,return=representation",
    )
    if not rows:
        raise DatabaseError("GitHub installation upsert returned no rows")
    return rows[0]


def get_github_installation_for_workspace(
    workspace_id: str, installation_id: int
) -> dict | None:
    """Return one github_installations row for a workspace + installation_id."""
    rows = _send_supabase_table_request(
        "github_installations",
        "GET",
        query_params={
            "select": "id,workspace_id,installation_id,account_login,app_slug",
            "workspace_id": f"eq.{workspace_id}",
            "installation_id": f"eq.{installation_id}",
            "limit": 1,
        },
    )
    if not rows:
        return None
    return rows[0]


def find_repository_by_installation_and_repo_id(
    installation_id: int, github_repo_id: int
) -> dict | None:
    """Find a V2 repository by GitHub App installation and repository IDs."""
    installation_rows = _send_supabase_table_request(
        "github_installations",
        "GET",
        query_params={
            "select": "id,workspace_id,installation_id",
            "installation_id": f"eq.{installation_id}",
            "limit": 1,
        },
    )
    if not installation_rows:
        return None

    installation = installation_rows[0]
    repository_rows = _send_supabase_table_request(
        "repositories",
        "GET",
        query_params={
            "select": "id,workspace_id,full_name,monitoring_enabled",
            "workspace_id": f"eq.{installation['workspace_id']}",
            "github_installation_id": f"eq.{installation['id']}",
            "github_repo_id": f"eq.{github_repo_id}",
            "limit": 1,
        },
    )
    if not repository_rows:
        return None

    repository = repository_rows[0]
    return {
        "workspace_id": repository.get("workspace_id"),
        "repository_id": repository.get("id"),
        "full_name": repository.get("full_name"),
        "monitoring_enabled": bool(repository.get("monitoring_enabled")),
        "github_installation_id": installation.get("installation_id"),
    }


def find_scan_event_by_delivery(
    workspace_id: str, repository_id: str, github_delivery_id: str
) -> dict | None:
    """Return an existing scan event for a workspace/repository delivery."""
    rows = _send_supabase_table_request(
        "scan_events",
        "GET",
        query_params={
            "select": (
                "id,workspace_id,repository_id,github_delivery_id,event_type,"
                "repo_full_name,branch,commit_sha,status,error_message,"
                "started_at,completed_at,created_at"
            ),
            "workspace_id": f"eq.{workspace_id}",
            "repository_id": f"eq.{repository_id}",
            "github_delivery_id": f"eq.{github_delivery_id}",
            "order": "created_at.desc",
            "limit": 1,
        },
    )
    if not rows:
        return None
    return rows[0]


def create_scan_event(scan_event_data: dict) -> dict:
    """Create a V2 scan event."""
    rows = _send_supabase_table_request(
        "scan_events",
        "POST",
        payload=scan_event_data,
    )
    if not rows:
        raise DatabaseError("Scan event insert returned no rows")
    return rows[0]


def update_scan_event_status(
    scan_event_id: str,
    status: str,
    error_message: str | None = None,
    completed_at: str | None = None,
) -> dict | None:
    """Update status fields on a V2 scan event."""
    payload = {
        "status": status,
        "error_message": error_message,
    }
    if completed_at is not None:
        payload["completed_at"] = completed_at

    rows = _send_supabase_table_request(
        "scan_events",
        "PATCH",
        query_params={
            "id": f"eq.{scan_event_id}",
            "select": (
                "id,workspace_id,repository_id,github_delivery_id,event_type,"
                "repo_full_name,branch,commit_sha,status,error_message,"
                "started_at,completed_at"
            ),
        },
        payload=payload,
    )
    if not rows:
        return None
    return rows[0]


def _safe_v2_detection_payload(detection_data: dict) -> dict:
    safe_data = {
        key: value
        for key, value in detection_data.items()
        if key in V2_DETECTION_FIELDS
    }
    safe_data.pop("raw_value", None)
    return safe_data


def create_v2_detection(detection_data: dict) -> dict:
    """Create one V2 detection without storing raw secret values."""
    rows = _send_supabase_table_request(
        "v2_detections",
        "POST",
        payload=_safe_v2_detection_payload(detection_data),
    )
    if not rows:
        raise DatabaseError("V2 detection insert returned no rows")
    return rows[0]


def create_v2_detections_bulk(detections: list[dict]) -> list[dict]:
    """Create V2 detections in bulk without storing raw secret values."""
    if not detections:
        return []

    rows = _send_supabase_table_request(
        "v2_detections",
        "POST",
        payload=[_safe_v2_detection_payload(detection) for detection in detections],
    )
    return rows


def _safe_v2_detection(row: dict) -> dict:
    return {field: row.get(field) for field in V2_DETECTION_SAFE_FIELDS}


def _safe_v2_scan_event(row: dict) -> dict:
    return {field: row.get(field) for field in V2_SCAN_EVENT_SAFE_FIELDS}


def get_v2_dashboard_overview(user_id: str) -> dict:
    """Return workspace-scoped V2 dashboard summary data."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return {
            "total_repositories": 0,
            "monitored_repositories": 0,
            "total_scan_events": 0,
            "completed_scan_events": 0,
            "failed_scan_events": 0,
            "total_detections": 0,
            "open_detections": 0,
            "critical_detections": 0,
            "high_detections": 0,
            "latest_scan_at": None,
        }

    repositories = _send_supabase_table_request(
        "repositories",
        "GET",
        query_params={
            "select": "id,monitoring_enabled",
            "workspace_id": f"eq.{workspace['id']}",
            "limit": 10000,
        },
    )
    scan_events = _send_supabase_table_request(
        "scan_events",
        "GET",
        query_params={
            "select": "id,status,started_at,completed_at,created_at",
            "workspace_id": f"eq.{workspace['id']}",
            "order": "created_at.desc",
            "limit": 10000,
        },
    )
    detections = _send_supabase_table_request(
        "v2_detections",
        "GET",
        query_params={
            "select": "id,status,severity",
            "workspace_id": f"eq.{workspace['id']}",
            "limit": 10000,
        },
    )

    latest_scan = scan_events[0] if scan_events else {}
    return {
        "total_repositories": len(repositories),
        "monitored_repositories": sum(
            1 for repository in repositories if repository.get("monitoring_enabled")
        ),
        "total_scan_events": len(scan_events),
        "completed_scan_events": sum(
            1 for scan_event in scan_events if scan_event.get("status") == "completed"
        ),
        "failed_scan_events": sum(
            1 for scan_event in scan_events if scan_event.get("status") == "failed"
        ),
        "total_detections": len(detections),
        "open_detections": sum(
            1 for detection in detections if detection.get("status") == "open"
        ),
        "critical_detections": sum(
            1 for detection in detections if detection.get("severity") == "critical"
        ),
        "high_detections": sum(
            1 for detection in detections if detection.get("severity") == "high"
        ),
        "latest_scan_at": latest_scan.get("started_at")
        or latest_scan.get("created_at")
        or latest_scan.get("completed_at"),
    }


def list_v2_scan_events(
    user_id: str, limit: int = 20, status: str | None = None
) -> list[dict]:
    """Return recent V2 scan events for the authenticated user's workspace."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return []

    query_params = {
        "select": ",".join(V2_SCAN_EVENT_SAFE_FIELDS),
        "workspace_id": f"eq.{workspace['id']}",
        "order": "created_at.desc",
        "limit": max(1, min(limit, 100)),
    }
    if status:
        query_params["status"] = f"eq.{status}"

    rows = _send_supabase_table_request(
        "scan_events",
        "GET",
        query_params=query_params,
    )
    return [_safe_v2_scan_event(row) for row in rows]


def list_v2_detections(user_id: str, filters: dict | None = None) -> list[dict]:
    """Return safe V2 detections for the authenticated user's workspace."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return []

    filters = filters or {}
    limit = max(1, min(int(filters.get("limit", 50)), 100))
    query_params = {
        "select": ",".join(V2_DETECTION_SAFE_FIELDS),
        "workspace_id": f"eq.{workspace['id']}",
        "order": "detected_at.desc",
        "limit": limit,
    }

    if filters.get("status"):
        query_params["status"] = f"eq.{str(filters['status']).lower()}"
    if filters.get("severity"):
        query_params["severity"] = f"eq.{str(filters['severity']).lower()}"
    if filters.get("repository_id"):
        query_params["repository_id"] = f"eq.{filters['repository_id']}"

    rows = _send_supabase_table_request(
        "v2_detections",
        "GET",
        query_params=query_params,
    )
    return [_safe_v2_detection(row) for row in rows]


def update_v2_detection_status(
    user_id: str, detection_id: str, status: str
) -> dict | None:
    """Update a workspace-owned V2 detection status."""
    normalized_status = status.lower()
    if normalized_status not in V2_ALLOWED_DETECTION_STATUSES:
        raise InvalidDetectionStatusError("Invalid V2 detection status")

    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return None

    existing = _send_supabase_table_request(
        "v2_detections",
        "GET",
        query_params={
            "select": "id",
            "id": f"eq.{detection_id}",
            "workspace_id": f"eq.{workspace['id']}",
            "limit": 1,
        },
    )
    if not existing:
        return None

    payload = {
        "status": normalized_status,
        "resolved_at": (
            datetime.now(timezone.utc).isoformat()
            if normalized_status == "resolved"
            else None
        ),
    }
    rows = _send_supabase_table_request(
        "v2_detections",
        "PATCH",
        query_params={
            "id": f"eq.{detection_id}",
            "workspace_id": f"eq.{workspace['id']}",
            "select": ",".join(V2_DETECTION_SAFE_FIELDS),
        },
        payload=payload,
    )
    if not rows:
        return None
    return _safe_v2_detection(rows[0])


def upsert_repositories_for_installation(
    workspace_id: str, github_installation_db_id: str, repositories: list[dict]
) -> list[dict]:
    """Upsert repositories for a workspace installation using github_repo_id."""
    if not repositories:
        return []

    payload_rows: list[dict] = []
    for repo in repositories:
        owner_data = repo.get("owner") or {}
        payload_rows.append(
            {
                "workspace_id": workspace_id,
                "github_installation_id": github_installation_db_id,
                "github_repo_id": repo.get("id"),
                "full_name": repo.get("full_name"),
                "owner": owner_data.get("login") or "",
                "name": repo.get("name") or "",
                "private": bool(repo.get("private", False)),
                "default_branch": repo.get("default_branch"),
                "html_url": repo.get("html_url"),
            }
        )

    rows = _send_supabase_table_request(
        "repositories",
        "POST",
        query_params={"on_conflict": "github_repo_id"},
        payload=payload_rows,
        prefer="resolution=merge-duplicates,return=representation",
    )
    return rows


def get_repositories_for_user_workspace(user_id: str) -> list[dict]:
    """Return repositories from the authenticated user's owned workspace."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return []

    return _send_supabase_table_request(
        "repositories",
        "GET",
        query_params={
            "select": (
                "id,github_repo_id,full_name,owner,name,private,default_branch,"
                "html_url,monitoring_enabled,created_at,updated_at"
            ),
            "workspace_id": f"eq.{workspace['id']}",
            "order": "full_name.asc",
        },
    )


def update_repository_monitoring(
    user_id: str, repository_id: str, monitoring_enabled: bool
) -> dict | None:
    """Update monitoring_enabled for a repository in the user's workspace."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return None

    existing = _send_supabase_table_request(
        "repositories",
        "GET",
        query_params={
            "select": "id",
            "id": f"eq.{repository_id}",
            "workspace_id": f"eq.{workspace['id']}",
            "limit": 1,
        },
    )
    if not existing:
        return None

    rows = _send_supabase_table_request(
        "repositories",
        "PATCH",
        query_params={
            "id": f"eq.{repository_id}",
            "workspace_id": f"eq.{workspace['id']}",
            "select": (
                "id,github_repo_id,full_name,owner,name,private,default_branch,"
                "html_url,monitoring_enabled,created_at,updated_at"
            ),
        },
        payload={"monitoring_enabled": monitoring_enabled},
    )
    if not rows:
        return None
    return rows[0]


def get_discord_webhooks_for_user_workspace(user_id: str) -> list[dict]:
    """Return Discord webhooks for the authenticated user's owned workspace."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return []

    return _send_supabase_table_request(
        "discord_webhooks",
        "GET",
        query_params={
            "select": (
                "id,workspace_id,name,webhook_url_last4,enabled,last_tested_at,"
                "last_error,created_by_user_id,created_at,updated_at"
            ),
            "workspace_id": f"eq.{workspace['id']}",
            "order": "created_at.asc",
        },
    )


def create_discord_webhook_for_user_workspace(
    user_id: str,
    name: str,
    webhook_url_ciphertext: str,
    webhook_url_last4: str,
    enabled: bool = True,
) -> dict | None:
    """Create a Discord webhook in the authenticated user's owned workspace."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return None

    rows = _send_supabase_table_request(
        "discord_webhooks",
        "POST",
        payload={
            "workspace_id": workspace["id"],
            "name": name,
            "webhook_url_ciphertext": webhook_url_ciphertext,
            "webhook_url_last4": webhook_url_last4,
            "enabled": enabled,
            "created_by_user_id": user_id,
        },
    )
    if not rows:
        return None
    return rows[0]


def get_discord_webhook_for_user_workspace(
    user_id: str, webhook_id: str, include_ciphertext: bool = False
) -> dict | None:
    """Get one workspace-owned Discord webhook by id."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return None

    select_fields = (
        "id,workspace_id,name,webhook_url_last4,enabled,last_tested_at,last_error,"
        "created_by_user_id,created_at,updated_at"
    )
    if include_ciphertext:
        select_fields = (
            "id,workspace_id,name,webhook_url_ciphertext,webhook_url_last4,enabled,"
            "last_tested_at,last_error,created_by_user_id,created_at,updated_at"
        )

    rows = _send_supabase_table_request(
        "discord_webhooks",
        "GET",
        query_params={
            "select": select_fields,
            "id": f"eq.{webhook_id}",
            "workspace_id": f"eq.{workspace['id']}",
            "limit": 1,
        },
    )
    if not rows:
        return None
    return rows[0]


def update_discord_webhook_for_user_workspace(
    user_id: str,
    webhook_id: str,
    patch_data: dict,
) -> dict | None:
    """Update a workspace-owned Discord webhook and return safe fields."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return None

    allowed = {
        "name",
        "enabled",
        "webhook_url_ciphertext",
        "webhook_url_last4",
        "last_tested_at",
        "last_error",
    }
    payload = {k: v for k, v in patch_data.items() if k in allowed}
    if not payload:
        return get_discord_webhook_for_user_workspace(user_id, webhook_id)

    rows = _send_supabase_table_request(
        "discord_webhooks",
        "PATCH",
        query_params={
            "id": f"eq.{webhook_id}",
            "workspace_id": f"eq.{workspace['id']}",
            "select": (
                "id,workspace_id,name,webhook_url_last4,enabled,last_tested_at,"
                "last_error,created_by_user_id,created_at,updated_at"
            ),
        },
        payload=payload,
    )
    if not rows:
        return None
    return rows[0]


def delete_discord_webhook_for_user_workspace(user_id: str, webhook_id: str) -> bool:
    """Delete a workspace-owned Discord webhook."""
    workspace = get_owned_workspace_for_user(user_id)
    if not workspace:
        return False

    rows = _send_supabase_table_request(
        "discord_webhooks",
        "DELETE",
        query_params={
            "id": f"eq.{webhook_id}",
            "workspace_id": f"eq.{workspace['id']}",
            "select": "id",
        },
    )
    return bool(rows)
