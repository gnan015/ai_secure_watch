from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "AI SecureWatch"
    app_env: str = "development"
    frontend_url: str = "http://localhost:5173"

    github_webhook_secret: str = ""
    github_token: str = ""

    gemini_api_key: str = ""

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    n8n_webhook_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
