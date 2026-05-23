import pytest
from investimentos.config import Settings

def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    s = Settings()
    assert s.anthropic_api_key == "sk-test-key"
    assert s.database_url == "sqlite:///./test.db"

def test_settings_defaults():
    s = Settings(anthropic_api_key="sk-x", database_url="sqlite:///./x.db")
    assert s.log_level == "INFO"
    assert s.langfuse_host == "http://localhost:3000"
    assert s.llm_model_default == "claude-sonnet-4-6"
    assert s.llm_model_light == "claude-haiku-4-5"

def test_settings_missing_api_key_raises():
    with pytest.raises(Exception):
        Settings(anthropic_api_key="", database_url="sqlite:///./x.db")
