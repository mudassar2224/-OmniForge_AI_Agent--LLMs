"""Video generation using Hugging Face Inference API."""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

async def generate_video(
    prompt: str,
    model: str = "Wan-AI/Wan2.2-T2V-A14B",
    output_dir: str = "artifacts/videos",
    api_key: str | None = None,
    duration_seconds: int = 8,
) -> dict[str, Any]:
    """Generate a video using Hugging Face."""
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
        
        # Use text_to_video which returns raw bytes
        video_bytes = await client.text_to_video(prompt, model=model)

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = out_path / f"video_{timestamp}.mp4"

        filepath.write_bytes(video_bytes)
        logger.info("Generated video saved to: %s", filepath)

        return {
            "success": True,
            "path": str(filepath.resolve()),
            "prompt": prompt,
            "model": model,
            "error": "",
        }
    except Exception as e:
        logger.exception("Video generation failed: %s", e)
        return {
            "success": False,
            "error": str(e),
            "path": "",
            "prompt": prompt,
            "model": model,
        }
