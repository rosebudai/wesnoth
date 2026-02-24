"""Nano Banana AI provider for img2img reskinning."""

import os
from utils.reskin.providers.base import ReskinProvider


class NanoBananaProvider(ReskinProvider):
    """Nano Banana img2img provider.

    Requires NANO_BANANA_API_KEY environment variable.
    """

    def __init__(self, model: str = "default"):
        self.api_key = os.environ.get("NANO_BANANA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "NANO_BANANA_API_KEY environment variable is required. "
                "Set it to your Nano Banana API key."
            )
        self.model = model

    def transform(self, image_path: str, prompt: str, params: dict) -> bytes:
        # TODO: Implement actual Nano Banana API call
        # Expected flow:
        #   1. Read image, base64 encode
        #   2. POST to Nano Banana img2img endpoint
        #   3. Return response image bytes
        raise NotImplementedError(
            "Nano Banana API integration pending. "
            "Use --dry-run (echo provider) for pipeline testing."
        )
