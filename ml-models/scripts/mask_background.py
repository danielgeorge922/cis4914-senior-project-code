"""Replace the plain black/gray table background in each crop with flat gray, so retrieval can only match on fruit."""
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFilter

ML_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = (ML_ROOT / "data/raw").resolve()
CROPS_CSV = ML_ROOT / "data/manifests/sharepoint_v1/crops.csv"
MASKS_CSV = ML_ROOT / "data/manifests/sharepoint_v1/masks.csv"
OUT_DIR = ML_ROOT / "data/transformed/sharepoint_v1_masked"
FILL = (124, 116, 104)  # ImageNet mean color, so the background carries no signal after normalization


def safe_output(path):
    path = Path(path).resolve()
    if path.is_relative_to(RAW_ROOT):
        raise RuntimeError(f"Refusing to write inside raw data: {path}")
    return path


def otsu(values):
    hist, _ = np.histogram(values, bins=256, range=(0, 256))
    hist = hist.astype(np.float64)  # int64 overflows when squared below
    total, cumulative, cumulative_mean = hist.sum(), np.cumsum(hist), np.cumsum(hist * np.arange(256))
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (cumulative_mean[-1] * cumulative - cumulative_mean * total) ** 2 / (cumulative * (total - cumulative))
    return int(np.nanargmax(between))


def fruit_mask(image, work=256):
    # Each photo's table is one plain color (gray, black or navy). Estimate it from the border, keep pixels whose
    # color is far from it, clean up, then fill holes (dark spots) by flood-filling the background from the border.
    small = image.copy()
    small.thumbnail((work, work))
    rgb = np.asarray(small, dtype=np.float64)
    ring = np.concatenate([rgb[:4].reshape(-1, 3), rgb[-4:].reshape(-1, 3),
                           rgb[:, :4].reshape(-1, 3), rgb[:, -4:].reshape(-1, 3)])
    distance = np.linalg.norm(rgb - np.median(ring, axis=0), axis=2)
    distance = np.clip(distance * 255 / max(distance.max(), 1), 0, 255)
    mask = Image.fromarray((distance > otsu(distance)).astype(np.uint8) * 255)
    mask = mask.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))  # close gaps
    mask = mask.filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))  # remove specks

    filled = mask.copy()
    width, height = filled.size
    border = [(x, 0) for x in range(width)] + [(x, height - 1) for x in range(width)]
    border += [(0, y) for y in range(height)] + [(width - 1, y) for y in range(height)]
    for point in border:
        if filled.getpixel(point) == 0:
            ImageDraw.floodfill(filled, point, 128)
    fruit = np.asarray(filled) != 128
    return Image.fromarray(fruit.astype(np.uint8) * 255).resize(image.size, Image.BILINEAR), float(fruit.mean())


def contact_sheet(paths, out_path, n=48, thumb=192, seed=4914):
    paths = random.Random(seed).sample(paths, min(n, len(paths)))
    cols = 8
    sheet = Image.new("RGB", (cols * thumb, ((len(paths) + cols - 1) // cols) * thumb), "white")
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        im.thumbnail((thumb, thumb))
        sheet.paste(im, ((i % cols) * thumb, (i // cols) * thumb))
    sheet.save(safe_output(out_path), quality=85)


def run(min_fraction=0.15, max_fraction=1.0):  # a crop with no visible background is fine
    crops = pd.read_csv(CROPS_CSV)
    crops = crops[crops.status.eq("ok")]
    out_dir = safe_output(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in crops.itertuples():
        image = Image.open(ML_ROOT / row.transformed_path).convert("RGB")
        mask, fraction = fruit_mask(image)
        masked = Image.composite(image, Image.new("RGB", image.size, FILL), mask)
        out_path = safe_output(out_dir / f"{row.sample_id}.jpg")
        masked.save(out_path, quality=92)
        status = "ok" if min_fraction <= fraction <= max_fraction else "mask_fail"
        rows.append({"sample_id": row.sample_id, "transformed_path": out_path.relative_to(ML_ROOT).as_posix(),
                     "fruit_fraction": round(fraction, 3), "status": status})
    masks = pd.DataFrame(rows)
    masks.to_csv(safe_output(MASKS_CSV), index=False)
    contact_sheet([str(ML_ROOT / p) for p in masks.transformed_path], out_dir / "_contact_sheet.jpg")
    print(f"Masked {len(masks)}; mask_fail: {masks.status.eq('mask_fail').sum()}; "
          f"median fruit fraction: {masks.fruit_fraction.median():.2f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
