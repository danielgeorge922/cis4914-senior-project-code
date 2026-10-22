"""Train Daniel's exterior_4plus EfficientNetB0 (same settings as notebooks/inital_models.ipynb) and export it for Triton."""
import json
from pathlib import Path

import torch

import mango_transfer as transfer

ML_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ML_ROOT / "data/manifests/sharepoint_jpg/annotations.jsonl"
MODEL_DIR = ML_ROOT.parent / "server/model_repository/classifier"

CONFIG = """name: "classifier"
backend: "onnxruntime"
max_batch_size: 8
input [{ name: "input", data_type: TYPE_FP32, dims: [3, 224, 224] }]
output [{ name: "logits", data_type: TYPE_FP32, dims: [%d] }]
"""


def main():
    torch.hub.set_dir(str(ML_ROOT / "runs/.torch-cache"))
    experiments = transfer.prepare_experiments(MANIFEST, ML_ROOT, seed=4914)
    results = transfer.run_training(
        {"exterior_4plus": experiments["exterior_4plus"]}, MANIFEST, ML_ROOT / "runs/four-model-transfer",
        architectures=["EfficientNetB0"], epochs=10, patience=3, learning_rate=1e-3, batch_size=16, seed=4914,
    )
    run_dir = results[("exterior_4plus", "EfficientNetB0")]["run_dir"]
    model, class_names = transfer.load_run(run_dir, device="cpu")

    (MODEL_DIR / "1").mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model, (torch.zeros(2, 3, 224, 224),), MODEL_DIR / "1/model.onnx",
        input_names=["input"], output_names=["logits"],
        dynamic_shapes={"x": {0: torch.export.Dim("batch", max=8)}}, external_data=False, opset_version=18,
    )
    (MODEL_DIR / "labels.json").write_text(json.dumps(class_names, indent=2), encoding="utf-8")
    (MODEL_DIR / "config.pbtxt").write_text(CONFIG % len(class_names), encoding="utf-8")
    print(f"Exported {run_dir} -> {MODEL_DIR}")


if __name__ == "__main__":
    main()
