import hashlib
import json
import logging

import httpx
import numpy as np

from app.config import Settings
from app.schemas import Kind

logger = logging.getLogger(__name__)


class InferenceUnavailable(RuntimeError):
    pass


class TritonClassifier:
    """Calls Triton's HTTP/REST (KServe v2) API, sending the image tensor as binary data."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.models: dict[Kind, str] = {"fruit": settings.fruit_model, "leaf": settings.leaf_model}
        self.client = httpx.AsyncClient(base_url=settings.triton_url, timeout=settings.triton_timeout_s)

    async def infer(self, kind: Kind, batch: np.ndarray) -> np.ndarray:
        tensor = np.ascontiguousarray(batch, dtype=np.float32)
        header = json.dumps(
            {
                "inputs": [
                    {
                        "name": self.settings.model_input,
                        "shape": list(tensor.shape),
                        "datatype": "FP32",
                        "parameters": {"binary_data_size": tensor.nbytes},
                    }
                ],
                "outputs": [
                    {"name": self.settings.model_output, "parameters": {"binary_data": False}}
                ],
            }
        ).encode()
        try:
            response = await self.client.post(
                f"/v2/models/{self.models[kind]}/infer",
                content=header + tensor.tobytes(),
                headers={
                    "Content-Type": "application/octet-stream",
                    "Inference-Header-Content-Length": str(len(header)),
                },
            )
        except httpx.HTTPError as error:
            raise InferenceUnavailable(f"Triton request failed: {error}") from error
        if response.status_code != 200:
            logger.error("Triton returned %s: %s", response.status_code, response.text[:500])
            raise InferenceUnavailable(f"Triton returned {response.status_code}")

        output = next(o for o in response.json()["outputs"] if o["name"] == self.settings.model_output)
        return np.asarray(output["data"], dtype=np.float32).reshape(output["shape"])

    async def aclose(self) -> None:
        await self.client.aclose()


class MockClassifier:
    """Deterministic fake logits seeded by each image's pixels, for development without Triton."""

    def __init__(self, num_classes: int):
        self.num_classes = num_classes

    async def infer(self, kind: Kind, batch: np.ndarray) -> np.ndarray:
        rows = []
        for image in batch:
            seed = int.from_bytes(hashlib.sha256(kind.encode() + image.tobytes()).digest()[:8])
            rows.append(np.random.default_rng(seed).normal(scale=3.0, size=self.num_classes))
        return np.stack(rows).astype(np.float32)

    async def aclose(self) -> None:
        pass

