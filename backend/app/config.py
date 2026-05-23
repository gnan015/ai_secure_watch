from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "AI SecureWatch"
    app_env: str = "development"
    frontend_url: str = "http://localhost:5173"

    github_webhook_secret: str = ""
    github_token: str = ""
    # TODO(V2): Replace the global GitHub token path with GitHub App credentials
    # and per-installation access tokens.
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_app_webhook_secret: str = ""
    github_app_client_id: str = ""
    github_app_client_secret: str = ""

    gemini_api_key: str = ""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    # TODO(V2): Add Supabase Auth JWT/audience settings for authenticated
    # dashboard APIs while keeping service-role usage backend-only.

    n8n_webhook_url: str = ""
    # TODO(V2): Move alert destinations to user/workspace-owned Discord
    # webhook records instead of one global deployment webhook.
    discord_webhook_encryption_key: str | None = None
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",extra="ignore")


settings = Settings()
