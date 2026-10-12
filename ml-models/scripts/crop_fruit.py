"""Crop each training photo to the mango (dropping the label card/ruler) with OWLv2 zero-shot detection."""
import argparse
import random
from pathlib import Path

import pandas as pd
import torch
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

ML_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = (ML_ROOT / "data/raw").resolve()
MANIFEST = ML_ROOT / "data/manifests/sharepoint_v1/training.csv"
CROPS_CSV = ML_ROOT / "data/manifests/sharepoint_v1/crops.csv"
OUT_DIR = ML_ROOT / "data/transformed/sharepoint_v1"
# OWL-ViT v1 is several times faster on CPU than OWLv2 and is enough for one fruit on a plain table.
MODEL = "google/owlvit-base-patch32"

register_heif_opener()


def safe_output(path):
    # Never write inside data/raw.
    path = Path(path).resolve()
    if path.is_relative_to(RAW_ROOT):
        raise RuntimeError(f"Refusing to write inside raw data: {path}")
    return path


def open_photo(path):
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def detect(image, processor, model, prompt):
    small = image.copy()
    small.thumbnail((1024, 1024))
    inputs = processor(text=[[prompt]], images=small, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    # OWLv2 pads to a square, so its boxes are scaled to the padded side; OWL-ViT boxes map to (height, width).
    side = max(small.size)
    size = (side, side) if "owlv2" in model.config.model_type else (small.height, small.width)
    result = processor.post_process_grounded_object_detection(outputs, threshold=0.0, target_sizes=[size])[0]
    if len(result["scores"]) == 0:
        return None, 0.0
    best = int(result["scores"].argmax())
    scale = image.width / small.width
    x0, y0, x1, y1 = (float(v) * scale for v in result["boxes"][best])
    x0, y0 = max(0.0, x0), max(0.0, y0)
    x1, y1 = min(float(image.width), x1), min(float(image.height), y1)
    return (x0, y0, x1, y1), float(result["scores"][best])


def pad_box(box, width, height, pad=0.10):
    x0, y0, x1, y1 = box
    dx, dy = (x1 - x0) * pad, (y1 - y0) * pad
    return (int(max(0, x0 - dx)), int(max(0, y0 - dy)), int(min(width, x1 + dx)), int(min(height, y1 + dy)))


def contact_sheet(paths, out_path, n=48, thumb=192, seed=4914):
    paths = random.Random(seed).sample(paths, min(n, len(paths)))
    cols = 8
    sheet = Image.new("RGB", (cols * thumb, ((len(paths) + cols - 1) // cols) * thumb), "white")
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        im.thumbnail((thumb, thumb))
        sheet.paste(im, ((i % cols) * thumb, (i // cols) * thumb))
    sheet.save(safe_output(out_path), quality=85)


def run(limit=None, prompt="a mango fruit", min_score=0.2, model_name=MODEL):
    manifest = pd.read_csv(MANIFEST)
    if limit:
        manifest = manifest.head(limit)
    out_dir = safe_output(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    previous = pd.read_csv(CROPS_CSV).set_index("sample_id") if CROPS_CSV.exists() else pd.DataFrame()

    processor = AutoProcessor.from_pretrained(model_name)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(model_name).eval()

    rows = []
    for i, row in enumerate(manifest.itertuples(), 1):
        out_path = safe_output(out_dir / f"{row.sample_id}.jpg")
        if out_path.exists() and row.sample_id in previous.index:
            rows.append(previous.loc[row.sample_id].to_dict() | {"sample_id": row.sample_id})
            continue
        image = open_photo(ML_ROOT / row.raw_path)
        box, score = detect(image, processor, model, prompt)
        status = "ok" if box is not None and score >= min_score else "low_conf"
        if box is None:
            box = (0, 0, image.width, image.height)
        crop = image.crop(pad_box(box, image.width, image.height))
        crop.thumbnail((1024, 1024))
        crop.save(out_path, quality=92)
        rows.append({"sample_id": row.sample_id, "transformed_path": out_path.relative_to(ML_ROOT).as_posix(),
                     "x0": round(box[0]), "y0": round(box[1]), "x1": round(box[2]), "y1": round(box[3]),
                     "score": round(score, 4), "status": status})
        if i % 25 == 0:
            print(f"{i}/{len(manifest)} done", flush=True)
            pd.DataFrame(rows).to_csv(safe_output(CROPS_CSV), index=False)

    crops = pd.DataFrame(rows)[["sample_id", "transformed_path", "x0", "y0", "x1", "y1", "score", "status"]]
    crops.to_csv(safe_output(CROPS_CSV), index=False)
    contact_sheet([str(ML_ROOT / p) for p in crops.transformed_path], out_dir / "_contact_sheet.jpg")
    print(f"Cropped {len(crops)}; low_conf: {crops.status.eq('low_conf').sum()}; median score: {crops.score.median():.3f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--prompt", default="a mango fruit")
    parser.add_argument("--min-score", type=float, default=0.2)
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    run(args.limit, args.prompt, args.min_score, args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
