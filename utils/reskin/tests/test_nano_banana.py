import os
import pytest

from utils.reskin.providers.nano_banana import NanoBananaProvider


def test_init_reads_api_key_from_env(monkeypatch):
    monkeypatch.setenv("NANO_BANANA_API_KEY", "test-key-123")
    provider = NanoBananaProvider()
    assert provider.api_key == "test-key-123"


def test_init_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("NANO_BANANA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="NANO_BANANA_API_KEY"):
        NanoBananaProvider()
