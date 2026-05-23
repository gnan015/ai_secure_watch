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
