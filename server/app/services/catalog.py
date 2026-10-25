import json
import re
from pathlib import Path

from app.config import Settings

PLACEHOLDER_IMAGE = "/mango-placeholder.svg"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class Catalog:
    """Display information for each cultivar, keyed by the model's label name."""

    def __init__(self, entries: dict[str, dict]):
        self.entries = entries
        self.by_upper = {k.upper(): v for k, v in entries.items()}

    @classmethod
    def load(cls, path: Path) -> "Catalog":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def describe(self, label: str) -> dict:
        entry = self.by_upper.get(label.upper(), self.entries.get(label, {}))
        slug = slugify(label)
        default_image = f"/cultivars/{slug}.jpg"
        image = entry.get("image") or default_image
        return {
            "id": slug,
            "name": entry.get("name", label.title()),
            "image": image,
            "image_alt": entry.get(
                "imageAlt", f"Reference photograph of {label.title()} mango cultivar"
            ),
            "description": entry.get("description", f"Cultivar reference for {label.title()}."),
            "metadata": entry.get("metadata", []),
            "traits": entry.get("traits", []),
        }

    def ranges(self, label: str) -> dict:
        """Known measurement ranges, e.g. {"Fruit weight": [300, 700]}."""
        entry = self.by_upper.get(label.upper(), self.entries.get(label, {}))
        return entry.get("ranges", {})


def load_labels(settings: Settings, catalog: Catalog) -> list[str]:
    """Class names in model output order. Both models must share the same list."""
    if settings.mock_inference:
        return list(catalog.entries)
    path = settings.model_repository / settings.model / "labels.json"
    return json.loads(path.read_text(encoding="utf-8"))
