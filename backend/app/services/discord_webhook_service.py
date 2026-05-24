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


def _text_value(value: object, fallback: str = "unknown") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _truncate_text(value: object, max_length: int) -> str:
    text = _text_value(value, "")
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def _confidence_percent(value: object) -> str:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return "unknown"
    if confidence <= 1:
        confidence *= 100
    return f"{round(confidence)}%"


def _plain_detection_alert_content(detection: dict) -> str:
    severity = _text_value(detection.get("severity")).upper()
    branch = _text_value(detection.get("branch"))
    file_path = _text_value(detection.get("file_path"))
    line_number = _text_value(detection.get("line_number"))
    ai_reason = _truncate_text(detection.get("ai_reasoning"), 500)
    recommendation = _truncate_text(detection.get("ai_recommendation"), 700)
    pusher_name = _text_value(detection.get("pusher_name"), "")
    pusher_email = _text_value(detection.get("pusher_email"), "")
    pusher = " ".join(part for part in [pusher_name, pusher_email] if part).strip()

    sections = [
        f"⚠️ {severity} Risk Secret Detected",
        (
            f"Severity: {severity}\n"
            f"Repository: {_text_value(detection.get('repo_full_name'))}\n"
            f"Branch: {branch}\n"
            f"File: {file_path}\n"
            f"Line: {line_number}\n"
            f"Secret Type: {_text_value(detection.get('secret_type'))}\n"
            f"Masked Value: {_text_value(detection.get('masked_value'), 'masked')}\n"
            f"Detection Method: {_text_value(detection.get('detection_method'))}\n"
            f"Confidence: {_confidence_percent(detection.get('confidence_score'))}"
        ),
    ]

    if ai_reason:
        sections.append(f"AI Reason:\n{ai_reason}")
    if recommendation:
        sections.append(f"Recommendation:\n{recommendation}")
    if pusher:
        sections.append(f"Pusher:\n{pusher}")

    sections.append(f"Status:\n{_text_value(detection.get('status'), 'open')}")
    content = "\n\n".join(sections)
    if len(content) <= 1900:
        return content
    return f"{content[:1897]}..."


def _safe_detection_alert_payload(detection: dict) -> dict:
    return {"content": _plain_detection_alert_content(detection)}


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
