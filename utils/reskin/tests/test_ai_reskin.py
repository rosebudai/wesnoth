import io
import pytest
from PIL import Image

from utils.reskin.transforms.ai_reskin import build_prompt, ai_reskin
from utils.reskin.providers.echo import EchoProvider


def test_build_prompt_sprite():
    result = build_prompt("sprite", "cyberpunk neon style")
    assert "sprite" in result.lower()
    assert "cyberpunk neon style" in result
    assert "transparency" in result.lower()


def test_build_prompt_portrait():
    result = build_prompt("portrait", "fairy tale style")
    assert "portrait" in result.lower()
    assert "fairy tale style" in result


@pytest.fixture
def sample_sprite(tmp_path):
    img = Image.new("RGBA", (72, 72), (100, 100, 200, 255))
    path = tmp_path / "sprite.png"
    img.save(str(path))
    return str(path)


def test_ai_reskin_returns_bytes(sample_sprite):
    provider = EchoProvider()
    result = ai_reskin(sample_sprite, "sprite", "cyberpunk style", provider)
    assert isinstance(result, bytes)


def test_ai_reskin_produces_valid_image(sample_sprite):
    provider = EchoProvider()
    result = ai_reskin(sample_sprite, "sprite", "cyberpunk style", provider)
    img = Image.open(io.BytesIO(result))
    assert img.size == (72, 72)
