import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Kidzventure ERP"
    debug: bool = False

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_mode(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"development", "develop", "dev"}:
                return True
        return value

    # Set DEV_SQLITE=true for local run without PostgreSQL/Docker
    dev_sqlite: bool = False
    sqlite_path: str = "./kidzventure_dev.db"

    # Database — override via .env or environment variables
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kidzventure"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/kidzventure"

    @property
    def use_sqlite(self) -> bool:
        return self.dev_sqlite

    @property
    def effective_database_url(self) -> str:
        if self.dev_sqlite:
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        return self.database_url

    # JWT — MUST be overridden via JWT_SECRET env var in production
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://frontendbb.onrender.com"

    exotel_account_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_caller_id: str = ""
    exotel_api_base_url: str = "https://api.exotel.com"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_production_secrets(self) -> None:
        """Call on startup to ensure secrets are properly set."""
        if not self.jwt_secret:
            raise ValueError(
                "JWT_SECRET environment variable is not set. "
                "Generate a strong secret and set it before running in production: "
                "  python -c \"import secrets; print(secrets.token_hex(64))\""
            )
        if self.jwt_secret in ("dev-secret-change-in-production", "secret", "changeme"):
            import warnings
            warnings.warn(
                "WARNING: JWT_SECRET is set to a known weak default. "
                "Please set a strong random secret via the JWT_SECRET environment variable.",
                stacklevel=2,
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
