from kageko.setup import _build_toml, _build_env


def test_build_toml_openai():
    content = _build_toml("openai", "https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4o", "interactive")
    assert "[providers.openai]" in content
    assert 'api_key_env = "OPENAI_API_KEY"' in content
    assert 'model = "gpt-4o"' in content


def test_build_toml_ollama():
    content = _build_toml("ollama", "http://localhost:11434/v1", "", "llama3", "interactive")
    assert "[providers.ollama]" in content
    assert "api_key_env" not in content


def test_build_env():
    content = _build_env("OPENAI_API_KEY", "sk-test-123")
    assert "OPENAI_API_KEY=sk-test-123" in content


def test_build_env_empty_key():
    content = _build_env("MY_KEY", "")
    assert "MY_KEY=" in content
