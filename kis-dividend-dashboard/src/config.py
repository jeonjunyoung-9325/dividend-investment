"""Application settings loaded from environment or Streamlit secrets."""

from functools import lru_cache
from typing import Final, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ACCOUNT_PRODUCT_CODE_LENGTH = 2
DEFAULT_USD_KRW_FALLBACK: Final = "1350"


class Settings(BaseSettings):
    """Validated server-side configuration; secrets never belong in UI state."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=True
    )

    KIS_APP_KEY: SecretStr = SecretStr("")
    KIS_APP_SECRET: SecretStr = SecretStr("")
    KIS_ACCOUNT_NO: SecretStr = SecretStr("")
    KIS_ACCOUNT_PRODUCT_CODE: str = "01"
    KIS_MODE: Literal["real", "demo"] = "real"
    SUPABASE_DB_URL: SecretStr = SecretStr("")
    APP_PASSWORD_HASH: SecretStr = SecretStr("")
    SESSION_SECRET: SecretStr = SecretStr("")
    TOKEN_ENCRYPTION_KEY: SecretStr = SecretStr("")
    DEFAULT_USD_KRW_RATE: str = DEFAULT_USD_KRW_FALLBACK
    TOKEN_EXPIRY_BUFFER_MINUTES: int = Field(default=5, ge=1, le=60)
    SESSION_TIMEOUT_MINUTES: int = Field(default=30, ge=5, le=1440)
    TOKEN_LOCK_TIMEOUT_SECONDS: int = Field(default=5, ge=1, le=30)
    DEMO_MODE: bool = False

    @field_validator("KIS_ACCOUNT_PRODUCT_CODE")
    @classmethod
    def product_code_is_two_digits(cls, value: str) -> str:
        """Reject malformed account product codes at the config boundary."""
        if len(value) != ACCOUNT_PRODUCT_CODE_LENGTH or not value.isdigit():
            msg = "KIS_ACCOUNT_PRODUCT_CODE must contain two digits"
            raise ValueError(msg)
        return value

    @field_validator("DEFAULT_USD_KRW_RATE", mode="before")
    @classmethod
    def default_usd_rate_when_blank(cls, value: str) -> str:
        """Replace an empty deployment value with the documented fallback rate."""
        return value.strip() or DEFAULT_USD_KRW_FALLBACK

    def validate_runtime(self) -> None:
        """Require production secrets only outside demo mode."""
        if self.DEMO_MODE:
            return
        required = {
            "KIS_APP_KEY": self.KIS_APP_KEY,
            "KIS_APP_SECRET": self.KIS_APP_SECRET,
            "KIS_ACCOUNT_NO": self.KIS_ACCOUNT_NO,
            "SUPABASE_DB_URL": self.SUPABASE_DB_URL,
            "APP_PASSWORD_HASH": self.APP_PASSWORD_HASH,
            "SESSION_SECRET": self.SESSION_SECRET,
            "TOKEN_ENCRYPTION_KEY": self.TOKEN_ENCRYPTION_KEY,
        }
        missing = [name for name, value in required.items() if not value.get_secret_value()]
        if missing:
            msg = f"필수 Secret이 설정되지 않았습니다: {', '.join(missing)}"
            raise RuntimeError(msg)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-local immutable settings instance."""
    return Settings()
