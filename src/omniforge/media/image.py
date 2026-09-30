"""Image generation using Hugging Face Inference API."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any
import asyncio

logger = logging.getLogger(__name__)

async def generate_image(
    prompt: str,
    model: str = "black-forest-labs/FLUX.1-dev",
    output_dir: str = "artifacts/images",
    api_key: str | None = None,
) -> dict[str, Any]:
    """Generate an image using Hugging Face's API."""
    try:
        from huggingface_hub import AsyncInferenceClient
        from omniforge.config.settings import get_settings

        if not api_key:
            settings = get_settings()
            api_key = settings.HF_TOKEN

        if not api_key:
            return {
                "success": False,
                "error": "No Hugging Face token provided. Set HF_TOKEN in .env.",
                "path": "",
                "prompt": prompt,
                "model": model,
            }

        client = AsyncInferenceClient(token=api_key)
        image = await client.text_to_image(prompt, model=model)

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = out_path / f"image_{timestamp}.png"
        
        # Save image (PIL Image)
        image.save(filepath)
        logger.info("Generated image saved to: %s", filepath)

        return {
            "success": True,
            "path": str(filepath.resolve()),
            "prompt": prompt,
            "model": model,
            "error": "",
        }
    except Exception as e:
        logger.exception("Image generation failed: %s", e)
        return {
            "success": False,
            "error": str(e),
            "path": "",
            "prompt": prompt,
            "model": model,
        }
