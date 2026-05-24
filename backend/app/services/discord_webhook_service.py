from datetime import datetime, timezone

import requests
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class DiscordWebhookServiceError(Exception):
    """Raised when Discord webhook encryption/decryption/sending fails."""


def _get_fernet() -> Fernet:
    key = settings.discord_webhook_encryption_key
    if not key:
        raise DiscordWebhookServiceError(
            "DISCORD_WEBHOOK_ENCRYPTION_KEY is not configured"
        )
    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise DiscordWebhookServiceError(
            "DISCORD_WEBHOOK_ENCRYPTION_KEY is invalid"
        ) from exc


def mask_webhook_last4(webhook_url: str) -> str:
    stripped = webhook_url.strip()
    if len(stripped) >= 4:
        return stripped[-4:]
    return stripped


def encrypt_webhook_url(webhook_url: str) -> str:
    fernet = _get_fernet()
    try:
        encrypted = fernet.encrypt(webhook_url.strip().encode("utf-8"))
        return encrypted.decode("utf-8")
    except Exception as exc:
        raise DiscordWebhookServiceError("Failed to encrypt Discord webhook URL") from exc


def decrypt_webhook_url(webhook_url_ciphertext: str) -> str:
    fernet = _get_fernet()
    try:
        plaintext = fernet.decrypt(webhook_url_ciphertext.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken as exc:
        raise DiscordWebhookServiceError(
            "Failed to decrypt Discord webhook URL"
        ) from exc
    except Exception as exc:
        raise DiscordWebhookServiceError(
            "Failed to decrypt Discord webhook URL"
        ) from exc


def send_test_webhook_message(webhook_url: str, workspace_name: str | None = None) -> None:
    message = {
        "content": (
            "AI SecureWatch test alert: Discord webhook is configured correctly."
            f" Workspace: {workspace_name or 'unknown'}."
            f" Sent at {datetime.now(timezone.utc).isoformat()}."
        )
    }

    try:
        response = requests.post(webhook_url, json=message, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DiscordWebhookServiceError(
            "Failed to send Discord webhook test message"
        ) from exc


def _safe_detection_alert_payload(detection: dict) -> dict:
    return {
        "content": "AI SecureWatch detected a potential secret exposure.",
        "embeds": [
            {
                "title": "Secret detection",
                "color": 0xDA3633
                if detection.get("severity") == "critical"
                else 0xD29922,
                "fields": [
                    {
                        "name": "Repository",
                        "value": detection.get("repo_full_name") or "unknown",
                        "inline": True,
                    },
                    {
                        "name": "Severity",
                        "value": detection.get("severity") or "unknown",
                        "inline": True,
                    },
                    {
                        "name": "Secret type",
                        "value": detection.get("secret_type") or "unknown",
                        "inline": True,
                    },
                    {
                        "name": "Masked value",
                        "value": detection.get("masked_value") or "masked",
                        "inline": False,
                    },
                    {
                        "name": "Location",
                        "value": (
                            f"{detection.get('file_path') or 'unknown'}:"
                            f"{detection.get('line_number') or 'unknown'}"
                        ),
                        "inline": False,
                    },
                    {
                        "name": "Commit",
                        "value": detection.get("commit_sha") or "unknown",
                        "inline": True,
                    },
                    {
                        "name": "Status",
                        "value": detection.get("status") or "open",
                        "inline": True,
                    },
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }


def send_detection_alert(webhook_url: str, detection: dict) -> None:
    """Send one V2 detection alert to Discord using masked detection fields only."""
    try:
        payload = _safe_detection_alert_payload(detection)
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise DiscordWebhookServiceError(
            "Failed to send Discord detection alert"
        ) from exc
