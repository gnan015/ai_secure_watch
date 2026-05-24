from datetime import datetime, timedelta, timezone

import jwt
import requests

from app.config import settings


class GitHubAppServiceError(Exception):
    """Raised when a GitHub App request or configuration fails."""


def _require_github_app_settings() -> None:
    if not settings.github_app_id:
        raise GitHubAppServiceError("GITHUB_APP_ID is not configured")
    if not settings.github_app_private_key:
        raise GitHubAppServiceError("GITHUB_APP_PRIVATE_KEY is not configured")


def _normalized_private_key() -> str:
    # Private keys are often stored with escaped newlines in environment vars.
    return settings.github_app_private_key.replace("\\n", "\n")


def generate_app_jwt() -> str:
    """Generate a short-lived GitHub App JWT signed with RS256."""
    _require_github_app_settings()

    now = datetime.now(timezone.utc)
    payload = {
        "iat": int((now - timedelta(seconds=60)).timestamp()),
        "exp": int((now + timedelta(minutes=9)).timestamp()),
        "iss": settings.github_app_id,
    }

    token = jwt.encode(payload, _normalized_private_key(), algorithm="RS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def _github_app_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {generate_app_jwt()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_installation_access_token(installation_id: int) -> dict:
    """Create an installation access token for a GitHub App installation."""
    url = (
        f"https://api.github.com/app/installations/"
        f"{installation_id}/access_tokens"
    )

    try:
        response = requests.post(url, headers=_github_app_headers(), timeout=30)
    except requests.RequestException as exc:
        raise GitHubAppServiceError("Failed to reach GitHub access token API") from exc

    if response.status_code >= 400:
        raise GitHubAppServiceError(
            f"GitHub access token API failed with status {response.status_code}"
        )

    payload = response.json()
    return {
        "token": payload.get("token"),
        "expires_at": payload.get("expires_at"),
    }


def get_installation(installation_id: int) -> dict:
    """Fetch GitHub App installation metadata."""
    url = f"https://api.github.com/app/installations/{installation_id}"

    try:
        response = requests.get(url, headers=_github_app_headers(), timeout=30)
    except requests.RequestException as exc:
        raise GitHubAppServiceError("Failed to reach GitHub installation API") from exc

    if response.status_code >= 400:
        raise GitHubAppServiceError(
            f"GitHub installation API failed with status {response.status_code}"
        )

    return response.json()


def list_installation_repositories(installation_id: int) -> list[dict]:
    """List repositories accessible to a GitHub App installation."""
    access_token_payload = get_installation_access_token(installation_id)
    access_token = access_token_payload.get("token")
    if not access_token:
        raise GitHubAppServiceError("GitHub installation access token is missing")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    repositories: list[dict] = []
    page = 1
    per_page = 100

    while True:
        try:
            response = requests.get(
                "https://api.github.com/installation/repositories",
                headers=headers,
                params={"per_page": per_page, "page": page},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise GitHubAppServiceError(
                "Failed to reach GitHub installation repositories API"
            ) from exc

        if response.status_code >= 400:
            raise GitHubAppServiceError(
                "GitHub installation repositories API failed with status "
                f"{response.status_code}"
            )

        payload = response.json()
        page_repositories = payload.get("repositories") or []
        repositories.extend(page_repositories)

        if len(page_repositories) < per_page:
            break

        page += 1

    return repositories
