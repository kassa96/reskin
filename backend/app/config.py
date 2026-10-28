from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    meta_api_key: str = Field(validation_alias=AliasChoices("META_API_KEY", "MODEL_API_KEY"))
    meta_base_url: str = "https://api.meta.ai/v1"
    max_upload_mb: int = 10
    allowed_mime_types: set[str] = {"image/jpeg", "image/png", "image/webp"}
    cors_origins: list[str] = ["http://localhost:4200"]
    image_model: str = "muse-image-1.0"
    meta_timeout_seconds: float = 90.0
    prompt_model: str = "muse-wonder-1.0"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("meta_api_key")
    @classmethod
    def meta_api_key_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("META_API_KEY must not be empty")
        return value


settings = Settings()
