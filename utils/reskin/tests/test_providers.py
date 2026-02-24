import os
import pytest
from PIL import Image
import io

from utils.reskin.providers.base import ReskinProvider
from utils.reskin.providers.echo import EchoProvider


@pytest.fixture
def sample_image(tmp_path):
    """Create a small test PNG image."""
    img = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
    path = tmp_path / "test.png"
    img.save(str(path))
    return str(path)


def test_base_provider_is_abstract():
    provider = ReskinProvider()
    with pytest.raises(NotImplementedError):
        provider.transform("path.png", "prompt", {})


def test_echo_provider_returns_original_bytes(sample_image):
    provider = EchoProvider()
    result = provider.transform(sample_image, "any prompt", {})
    assert isinstance(result, bytes)
    # Verify it's a valid image
    img = Image.open(io.BytesIO(result))
    assert img.size == (32, 32)


def test_echo_provider_preserves_transparency(tmp_path):
    """Echo provider must preserve RGBA transparency."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    path = tmp_path / "transparent.png"
    img.save(str(path))

    provider = EchoProvider()
    result = provider.transform(str(path), "prompt", {})
    result_img = Image.open(io.BytesIO(result))
    assert result_img.mode == "RGBA"
