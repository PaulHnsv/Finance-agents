from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    github_token: str
    database_url: str = "sqlite:///./data/investimentos.db"
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "http://localhost:3000"
    brapi_token: str = ""
    log_level: str = "INFO"
    llm_base_url: str = "https://models.github.ai/inference"
    llm_model_default: str = "openai/gpt-4o"
    llm_model_light: str = "openai/gpt-4o-mini"

    @field_validator("github_token")
    @classmethod
    def api_key_must_not_be_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("GITHUB_TOKEN must not be empty")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
