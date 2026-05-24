import pytest
from investimentos.config import Settings, get_settings

def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp-test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    get_settings.cache_clear()
    s = Settings()
    assert s.github_token == "ghp-test"
    assert s.database_url == "sqlite:///./test.db"

def test_settings_defaults():
    s = Settings(github_token="ghp-x", database_url="sqlite:///./x.db")
    assert s.log_level == "INFO"
    assert s.langfuse_host == "http://localhost:3000"
    assert s.llm_base_url == "https://models.github.ai/inference"
    assert s.llm_model_default == "openai/gpt-4o"
    assert s.llm_model_light == "openai/gpt-4o-mini"

def test_settings_missing_token_raises():
    with pytest.raises(Exception):
        Settings(github_token="", database_url="sqlite:///./x.db")
