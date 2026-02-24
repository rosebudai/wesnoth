"""Echo provider — returns the original image unchanged. For testing."""

import io
from PIL import Image
from utils.reskin.providers.base import ReskinProvider


class EchoProvider(ReskinProvider):
    """Returns the original image unchanged. Useful for testing the pipeline."""

    def transform(self, image_path: str, prompt: str, params: dict) -> bytes:
        img = Image.open(image_path)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
