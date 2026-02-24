"""AI-powered reskinning via img2img providers."""

from utils.reskin.providers.base import ReskinProvider

PROMPT_TEMPLATES = {
    "sprite": (
        "Reskin this 2D pixel art game unit sprite. "
        "Preserve transparency, silhouette, and animation pose. "
        "Style: {style}"
    ),
    "portrait": (
        "Reskin this fantasy character portrait. "
        "Preserve face composition and expression. "
        "Style: {style}"
    ),
}


def build_prompt(category: str, style_prompt: str) -> str:
    """Build a full prompt from asset category and theme style prompt."""
    template = PROMPT_TEMPLATES.get(category, PROMPT_TEMPLATES["sprite"])
    return template.format(style=style_prompt)


def ai_reskin(
    image_path: str,
    category: str,
    style_prompt: str,
    provider: ReskinProvider,
    params: dict = None,
) -> bytes:
    """Reskin an image using an AI provider.

    Args:
        image_path: Path to source image.
        category: Asset category ("sprite" or "portrait").
        style_prompt: Theme style prompt.
        provider: ReskinProvider instance.
        params: Optional provider-specific parameters.

    Returns:
        Reskinned image as bytes.
    """
    prompt = build_prompt(category, style_prompt)
    return provider.transform(image_path, prompt, params or {})
