"""Write a saved mango_transfer run's validation or test predictions as a shortlist CSV (query, true, shortlist)."""
import argparse
import json
from pathlib import Path

import pandas as pd
import torch

from mango_transfer import choose_device, load_run, make_loader

ML_ROOT = Path(__file__).resolve().parents[1]


def write_shortlist(run_dir, out_csv, top_k=10, split="validation", num_workers=0):
    split = {"val": "validation"}.get(split, split)  # the manifest says val, mango_transfer says validation
    saved = json.loads((Path(run_dir) / "experiment.json").read_text())
    photos = pd.DataFrame([row for row in saved["split_rows"] if row["split"] == split])
    photos["image_path"] = photos.raw_path.map(lambda p: str(ML_ROOT / p))
    device = choose_device()
    model, names = load_run(run_dir, device)
    logits = []
    with torch.no_grad():
        for images, _ in make_loader({"splits": {split: photos}}, split, num_workers=num_workers):
            logits.append(model(images.to(device)).cpu())
    ranked = torch.cat(logits).argsort(dim=1, descending=True, stable=True)[:, :top_k]
    rows = pd.DataFrame({"query": photos.raw_path, "true": photos.class_name,
                         "shortlist": [json.dumps([names[i] for i in r]) for r in ranked.tolist()]})
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    rows.to_csv(out_csv, index=False)
    return out_csv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="Folder with head.pt and experiment.json.")
    parser.add_argument("--split", default="validation", help="validation while choosing models; test once at the end.")
    parser.add_argument("--out", type=Path, help="Defaults to <run_dir>/shortlist.csv.")
    args = parser.parse_args()
    print(write_shortlist(args.run_dir, args.out or args.run_dir / "shortlist.csv", split=args.split))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
