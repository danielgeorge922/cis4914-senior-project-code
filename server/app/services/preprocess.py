import io

import numpy as np
from PIL import Image, ImageOps

from app.config import Settings


def load_image(data: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(data))
    # Phone photos are often stored sideways with an EXIF rotation flag.
    return ImageOps.exif_transpose(image).convert("RGB")


def to_tensor(image: Image.Image, settings: Settings) -> np.ndarray:
    """Resize the photo the way the chosen model saw it in training, then normalize to a CHW float32 array."""
    if settings.model == "classifier":
        # Pad to a square, then resize (mango_transfer.PadResize).
        image = ImageOps.pad(
            image,
            (settings.image_size, settings.image_size),
            method=Image.Resampling.BILINEAR,
            color=settings.pad_color,
        )
    else:
        # Resize the short side, then center-crop (the DINOv2 processor).
        width, height = image.size
        scale = settings.resize_size / min(width, height)
        image = image.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            Image.Resampling.BICUBIC,
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
