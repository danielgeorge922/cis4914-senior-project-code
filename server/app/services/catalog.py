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

    @classmethod
    def load(cls, path: Path) -> "Catalog":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def describe(self, label: str) -> dict:
        entry = self.entries.get(label, {})
        return {
            "id": slugify(label),
            "name": entry.get("name", label),
            "image": entry.get("image", PLACEHOLDER_IMAGE),
            "image_alt": entry.get(
                "imageAlt", "Placeholder mango illustration, not a cultivar reference photograph"
            ),
            "description": entry.get("description", "Reference information has not been added yet."),
            "metadata": entry.get("metadata", []),
            "traits": entry.get("traits", []),
        }

    def ranges(self, label: str) -> dict:
        """Known measurement ranges, e.g. {"Fruit weight": [300, 700]}."""
        return self.entries.get(label, {}).get("ranges", {})


def load_labels(settings: Settings, catalog: Catalog) -> list[str]:
    """Class names in model output order. Both models must share the same list."""
    if settings.mock_inference:
        return list(catalog.entries)
    path = settings.model_repository / settings.fruit_model / "labels.json"
    return json.loads(path.read_text(encoding="utf-8"))
