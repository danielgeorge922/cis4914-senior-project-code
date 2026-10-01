from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVER_DIR / ".env", extra="ignore")

    # Random but repeatable scores, so the API works without Triton or trained models.
    mock_inference: bool = False

    triton_url: str = "http://localhost:8000"
    triton_timeout_s: float = 30.0
    fruit_model: str = "fruit_classifier"
    leaf_model: str = "leaf_classifier"
    model_input: str = "input"
    model_output: str = "logits"
    model_repository: Path = SERVER_DIR / "model_repository"
    catalog_path: Path = SERVER_DIR / "data" / "cultivars.json"

    # Must match the evaluation transform used in training.
    resize_size: int = 256
    image_size: int = 224
    norm_mean: tuple[float, float, float] = (0.485, 0.456, 0.406)
    norm_std: tuple[float, float, float] = (0.229, 0.224, 0.225)

    top_k: int = 10
    # Score multiplier for each measurement outside a cultivar's known range.
    range_penalty: float = 0.5

    allowed_origins: list[str] = ["http://localhost:3000"]
