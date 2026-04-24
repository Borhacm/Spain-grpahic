from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Spain Data Editorial Backend"
    app_env: Literal["local", "dev", "prod", "test"] = "local"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/editorial_data"
    )

    request_timeout_seconds: float = 20.0
    request_retries: int = 3
    request_backoff_seconds: float = 1.0

    aemet_api_key: str | None = None
    cnmv_registry_url: str | None = None
    country_overview_bde_url: str | None = None
    country_overview_ine_url: str | None = None
    country_overview_eurostat_url: str | None = None
    country_overview_oecd_url: str | None = None
    country_overview_fmi_url: str | None = None
    country_overview_series_map: str | None = None

    scheduler_enabled: bool = False
    scheduler_timezone: str = "Europe/Madrid"
    scheduler_ingest_ine_enabled: bool = True
    scheduler_ingest_bde_enabled: bool = True
    scheduler_ingest_oecd_enabled: bool = True
    scheduler_ingest_fmi_enabled: bool = True
    scheduler_ingest_ine_cron: str = "15 6 * * *"
    scheduler_ingest_bde_cron: str = "45 6 * * 1,3,5"
    scheduler_ingest_oecd_cron: str = "30 7 * * 1"
    scheduler_ingest_fmi_cron: str = "40 7 * * 1"
    scheduler_bde_codes: str = ""
    scheduler_oecd_codes: str = "GOV_DGOGD_2025:DG:ESP,GOV_DGOGD_2025:OUR:ESP"
    scheduler_fmi_codes: str = "NGDP_RPCH,PCPIPCH,LUR"
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    api_keys: str = ""
    api_default_role: Literal["viewer", "editor", "admin"] = "viewer"
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_postgres_driver(cls, v: Any) -> Any:
        if not isinstance(v, str):
            return v
        if "postgresql+psycopg" in v or "postgres+psycopg" in v:
            return v
        if v.startswith("postgresql://"):
            return "postgresql+psycopg://" + v.removeprefix("postgresql://")
        if v.startswith("postgres://"):
            return "postgresql+psycopg://" + v.removeprefix("postgres://")
        return v


class _SettingsLoader:
    """Callable settings loader (tests may call ``cache_clear()``; no in-process memoization)."""

    def __call__(self) -> Settings:
        return Settings()

    def cache_clear(self) -> None:
        """Compatibility with older tests; settings are re-read from the environment each call."""
        return None


get_settings = _SettingsLoader()
