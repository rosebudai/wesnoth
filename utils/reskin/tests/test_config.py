import json
import os
import pytest
import tempfile

from utils.reskin.config import load_theme, ThemeConfig, ValidationError


@pytest.fixture
def cyberpunk_theme_data():
    return {
        "name": "cyberpunk",
        "description": "Neon-lit sci-fi warriors",
        "prompt": "cyberpunk neon sci-fi style, glowing circuits",
        "palette": {
            "browns": "#0a0a2e",
            "greens": "#00ff88"
        }
    }


@pytest.fixture
def theme_file(cyberpunk_theme_data, tmp_path):
    path = tmp_path / "cyberpunk.json"
    path.write_text(json.dumps(cyberpunk_theme_data))
    return str(path)


def test_load_theme_returns_theme_config(theme_file):
    theme = load_theme(theme_file)
    assert isinstance(theme, ThemeConfig)
    assert theme.name == "cyberpunk"
    assert theme.prompt == "cyberpunk neon sci-fi style, glowing circuits"
    assert theme.palette["browns"] == "#0a0a2e"


def test_load_theme_missing_file():
    with pytest.raises(FileNotFoundError):
        load_theme("/nonexistent/theme.json")


def test_load_theme_missing_required_field(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"name": "bad"}))
    with pytest.raises(ValidationError):
        load_theme(str(path))


def test_load_theme_by_name():
    """Load a theme by name from the themes/ directory."""
    theme = load_theme("cyberpunk")
    assert theme.name == "cyberpunk"
