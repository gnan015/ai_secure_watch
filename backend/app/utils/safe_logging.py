import json
import logging


LOGGER = logging.getLogger("ai_securewatch")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


SAFE_LOG_FIELDS = {
    "event_type",
    "delivery_id",
    "installation_id",
    "github_repo_id",
    "repo_full_name",
    "workspace_id",
    "repository_id",
    "scan_event_id",
    "status",
    "monitoring_enabled",
    "v2_repository_matched",
    "detections_found",
    "detections_stored",
    "detections_to_store",
    "error_type",
    "error_message",
}


def _safe_context(fields: dict) -> dict:
    return {
        key: value
        for key, value in fields.items()
        if key in SAFE_LOG_FIELDS and value is not None
    }


def log_safe(level: int, event: str, **fields) -> None:
    """Log structured metadata without secret-bearing fields."""
    LOGGER.log(
        level,
        json.dumps({"event": event, **_safe_context(fields)}, default=str),
    )
