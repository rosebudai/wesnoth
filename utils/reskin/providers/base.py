"""Base provider interface for reskin transforms."""


class ReskinProvider:
    """Abstract base class for reskin providers."""

    def transform(self, image_path: str, prompt: str, params: dict) -> bytes:
        """Transform an image according to the given style prompt.

        Args:
            image_path: Absolute path to the source image.
            prompt: Fully constructed style prompt.
            params: Additional provider-specific parameters.

        Returns:
            Reskinned image as bytes (PNG format).
        """
        raise NotImplementedError
