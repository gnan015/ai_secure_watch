from app.config import settings
import requests


N8N_SAFE_FIELDS = {
    "detection_id",
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
    "severity",
    "confidence_score",
    "ai_reasoning",
    "ai_recommendation",
    "status",
    "pusher_name",
    "pusher_email",
    "detected_at",
}


def _build_safe_n8n_payload(detection_data: dict) -> dict:
    """Build a webhook payload that never includes raw secret values."""
    payload = {
        key: value
        for key, value in detection_data.items()
        if key in N8N_SAFE_FIELDS
    }

    if "detection_id" not in payload and detection_data.get("id"):
        payload["detection_id"] = detection_data["id"]

    # Defensive removal in case a future caller passes raw_value by mistake.
    payload.pop("raw_value", None)

    return payload


def send_detection_to_n8n(detection_data: dict) -> bool:
    """Send safe stored detection details to an n8n webhook."""
    if not settings.n8n_webhook_url:
        print("n8n webhook URL is not configured")
        return False

    try:
        # FastAPI handles detection and Supabase storage. n8n handles later
        # automation and alerting. Only masked secrets are sent to n8n.
        payload = _build_safe_n8n_payload(detection_data)

        print("Sending detection to n8n")
        response = requests.post(
            settings.n8n_webhook_url,
            json=payload,
            timeout=10,
        )
        response.raise_for_status()

        print("Detection sent to n8n successfully")
        return True
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        print(f"Failed to send detection to n8n: HTTP {status_code}")
        return False
    except requests.exceptions.RequestException as exc:
        print(f"Failed to send detection to n8n: {type(exc).__name__}")
        return False
    except Exception as exc:
        print(f"Failed to send detection to n8n: {type(exc).__name__}")
        return False
