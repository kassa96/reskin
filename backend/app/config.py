from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    fal_key: str
    anthropic_api_key: str
    max_upload_mb: int = 10
    allowed_mime_types: set[str] = {"image/jpeg", "image/png", "image/webp"}
    cors_origins: list[str] = ["http://localhost:4200"]
    fal_model: str = "fal-ai/nano-banana/edit"
    fal_text_to_image_model: str = "fal-ai/nano-banana"
    fal_timeout_seconds: float = 90.0
    prompt_model: str = "claude-opus-4-8"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("fal_key")
    @classmethod
    def fal_key_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("FAL_KEY must not be empty")
        return value

    @field_validator("anthropic_api_key")
    @classmethod
    def anthropic_api_key_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ANTHROPIC_API_KEY must not be empty")
        return value


settings = Settings()
