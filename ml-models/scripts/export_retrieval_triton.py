"""Export the DINOv2 retrieval model (retrieval_baseline.py) for Triton, with the saved gallery built in."""
import json

import numpy as np
import pandas as pd
import torch
from transformers import AutoModel

from retrieval_baseline import MANIFEST, ML_ROOT, MODEL, RUN_DIR

MODEL_DIR = ML_ROOT.parent / "server/model_repository/retrieval"
# Cosine similarities sit close together, so scale them before the server's softmax.
SCALE = 20.0

CONFIG = """name: "retrieval"
backend: "onnxruntime"
max_batch_size: 8
input [{ name: "input", data_type: TYPE_FP32, dims: [3, 224, 224] }]
output [{ name: "logits", data_type: TYPE_FP32, dims: [%d] }]
"""


class Retrieval(torch.nn.Module):
    """Each cultivar's score is its best match among the gallery photos, as in retrieval_baseline.evaluate."""

    def __init__(self, gallery, labels, class_names):
        super().__init__()
        self.dino = AutoModel.from_pretrained(MODEL).eval()
        self.register_buffer("gallery", torch.from_numpy(gallery))
        mask = np.array([[label == name for label in labels] for name in class_names])
        self.register_buffer("mask", torch.from_numpy(mask))

    def forward(self, x):
        vector = torch.nn.functional.normalize(self.dino(pixel_values=x).pooler_output, dim=1)
        sims = vector @ self.gallery.T
        best = sims[:, None, :].masked_fill(~self.mask, -1.0).amax(dim=2)
        return best * SCALE


def main():
    data = np.load(RUN_DIR / "embeddings.npz")
    labels = pd.read_csv(MANIFEST).set_index("sample_id").cultivar[data["sample_id"]].tolist()
    class_names = sorted(set(labels))
    model = Retrieval(data["embedding"].astype(np.float32), labels, class_names).eval()

    (MODEL_DIR / "1").mkdir(parents=True, exist_ok=True)
    with torch.no_grad():
        torch.onnx.export(
            model, (torch.zeros(2, 3, 224, 224),), MODEL_DIR / "1/model.onnx",
            input_names=["input"], output_names=["logits"],
            dynamic_shapes={"x": {0: torch.export.Dim("batch", max=8)}}, external_data=False, opset_version=18,
        )
    (MODEL_DIR / "labels.json").write_text(json.dumps(class_names, indent=2), encoding="utf-8")
    (MODEL_DIR / "config.pbtxt").write_text(CONFIG % len(class_names), encoding="utf-8")
    print(f"Exported {len(labels)} gallery photos, {len(class_names)} cultivars -> {MODEL_DIR}")


if __name__ == "__main__":
    main()
