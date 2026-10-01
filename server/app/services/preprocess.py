import io

import numpy as np
from PIL import Image, ImageOps

from app.config import Settings


def load_image(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    # Phone photos are often stored sideways with an EXIF rotation flag.
    return ImageOps.exif_transpose(image).convert("RGB")


def to_tensor(image: Image.Image, settings: Settings) -> np.ndarray:
    """Resize the short side, center-crop, and normalize to a CHW float32 array."""
    width, height = image.size
    scale = settings.resize_size / min(width, height)
    image = image.resize(
        (max(1, round(width * scale)), max(1, round(height * scale))),
        Image.Resampling.BILINEAR,
    )
    width, height = image.size
    left = (width - settings.image_size) // 2
    top = (height - settings.image_size) // 2
    image = image.crop((left, top, left + settings.image_size, top + settings.image_size))

    pixels = np.asarray(image, dtype=np.float32) / 255.0
    pixels = (pixels - np.array(settings.norm_mean, dtype=np.float32)) / np.array(
        settings.norm_std, dtype=np.float32
    )
    return pixels.transpose(2, 0, 1)
