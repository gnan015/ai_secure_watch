from app.config import settings
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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
