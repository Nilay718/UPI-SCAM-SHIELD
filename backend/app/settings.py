from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "UPI Scam Shield"
    cors_allow_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    cors_allow_credentials: bool = False
    max_upload_mb: int = 6
    allowed_image_content_types: str = "image/png,image/jpeg,image/webp"
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_models: str = (
        "google/gemini-2.0-flash-lite,openai/gpt-4o-mini,meta-llama/llama-3.1-8b-instruct"
    )
    # Optional: use a stronger model for intent/explanation (e.g. anthropic/claude-3.5-sonnet on OpenRouter)
    openrouter_model_intent: str | None = None
    openrouter_model_enrich: str | None = None
    llm_intent_enabled: bool = True
    llm_explanation_enrich_enabled: bool = True
    tesseract_cmd: str | None = None

    @property
    def openrouter_model_list(self) -> List[str]:
        return [m.strip() for m in self.openrouter_models.split(",") if m.strip()]

    @property
    def cors_allow_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def allowed_image_content_type_list(self) -> List[str]:
        return [t.strip().lower() for t in self.allowed_image_content_types.split(",") if t.strip()]


settings = Settings()

