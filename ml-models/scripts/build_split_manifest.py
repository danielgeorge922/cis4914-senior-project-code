"""Build the split_v1 manifest from Kyle's train/test folders, in the same columns as sharepoint_v1 plus split
and augmented columns.

Train is <split root>/train/augmented_data (originals + augmented copies), test is <split root>/test/preprocessed_data.
Rules (docs/adr/0001-split-v1-evaluation.md): a specimen (a photo, its copies and its burst shots) sits in one split;
val is ~10% of train specimens per cultivar; cultivars failing Daniel's 3plus rule are dropped and listed.
"""
import argparse
import hashlib
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from build_manifest import normalize

ML_ROOT = Path(__file__).resolve().parents[1]
SPLIT_ROOT = ML_ROOT.parent / "split_full"
FOLDERS = {"train": "train/augmented_data", "test": "test/preprocessed_data"}
VIEWS = {"fruit": "exterior", "leaves": "leaf"}
OUT_DIR = ML_ROOT / "data/manifests/split_v1"


BURST_SECONDS = 10
VAL_SHARE = 0.1


def original_name(stem):
    # Kyle's augmentation adds _orig / _augN; Roboflow copies add _0_jpg.rf.<hash>; downloads add " (N)".
    stem = re.sub(r"_(orig|aug\d+)$", "", stem)
    stem = re.sub(r"_\d+_jpg\.rf\.[0-9a-f]+$", "", stem)
    return re.sub(r" \(\d+\)$", "", stem)


def burst_specimens(names):
    # Phone photos named IMG_<date>_<time> each taken within BURST_SECONDS of the previous one are one fruit.
    times = {}
    for name in names:
        match = re.fullmatch(r"IMG_(\d{8}_\d{6})", name)
        if match:
            times[name] = pd.to_datetime(match.group(1), format="%Y%m%d_%H%M%S")
    specimen, first, last = {}, None, None
    for name in sorted(times, key=times.get):
        if last is None or (times[name] - last).total_seconds() > BURST_SECONDS:
            first = name
        specimen[name] = first
        last = times[name]
    return {name: specimen.get(name, name) for name in names}


def build(split_root=SPLIT_ROOT, out_dir=OUT_DIR, seed=4914):
    aliases = pd.read_csv(Path(out_dir) / "cultivar_aliases.csv")
    alias_map = dict(zip(aliases.raw.map(normalize), aliases.canonical.map(normalize)))
    rows = []
    for split, folder in FOLDERS.items():
        folder = Path(split_root) / folder
        for path in sorted(folder.rglob("*.jpg")):
            category, cultivar_raw = path.relative_to(folder).parts[:2]
            cultivar = normalize(cultivar_raw)
            cultivar = alias_map.get(cultivar, cultivar)
            raw_path = Path(os.path.relpath(path, ML_ROOT)).as_posix()
            rows.append({
                "sample_id": f"{split}/{category}/{cultivar_raw}/{path.stem}",
                "raw_path": raw_path,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "cultivar_raw": cultivar_raw,
                "cultivar": cultivar,
                "photo": original_name(path.stem),
                "view": VIEWS[category],
                "split": split,
                # Augmented and Roboflow copies are train data only; val/test are scored on originals.
                "augmented": bool(re.search(r"_aug\d+$|\.rf\.[0-9a-f]+| \(\d+\)", path.stem)),
            })
    out = pd.DataFrame(rows)
    # All copies and burst shots of one fruit are one specimen, so they never land in two splits.
    out["specimen"] = ""
    for (view, cultivar), group in out.groupby(["view", "cultivar"]):
        first = burst_specimens(group.photo.unique())
        out.loc[group.index, "specimen"] = view + "|" + cultivar + "|" + group.photo.map(first)
    # Kyle split photo by photo; a specimen goes to the side holding most of its originals (ties go to test).
    originals = out[~out.augmented]
    test_share = originals.split.eq("test").groupby(originals.specimen).mean()
    # Specimens with no original left (only copies) are train data only.
    out["split"] = out.specimen.map(test_share).ge(0.5).map({True: "test", False: "train"})
    out = out.drop(columns="photo")

    # Validation: about VAL_SHARE of each cultivar's train specimens that have an original, fixed seed.
    rng = np.random.default_rng(seed)
    for _, group in out[out.split.eq("train") & out.specimen.isin(test_share.index)].groupby(["view", "cultivar"]):
        specimens = sorted(group.specimen.unique())
        picked = rng.choice(specimens, size=max(1, round(VAL_SHARE * len(specimens))), replace=False)
        out.loc[out.specimen.isin(picked), "split"] = "val"

    # Daniel's 3plus rule: 4+ photos and 3+ specimens per cultivar, and every cultivar in every split.
    originals = out[~out.augmented]
    stats = originals.groupby(["view", "cultivar"]).agg(
        photos=("sample_id", "size"), specimens=("specimen", "nunique"), splits=("split", "nunique"))
    # Cultivars with no originals at all still get listed as dropped.
    stats = stats.reindex(out.groupby(["view", "cultivar"]).size().index, fill_value=0)
    keep = stats.photos.ge(4) & stats.specimens.ge(3) & stats.splits.eq(3)
    stats[~keep].reset_index().to_csv(Path(out_dir) / "dropped_cultivars.csv", index=False)
    out = out[out.set_index(["view", "cultivar"]).index.isin(stats[keep].index)].reset_index(drop=True)

    if out.groupby("specimen").split.nunique().gt(1).any():
        raise ValueError("A specimen is in more than one split.")
    out.to_csv(Path(out_dir) / "training.csv", index=False)
    # Photos are already preprocessed, so the "crop" is the photo itself (lets retrieval_baseline.load_samples read it).
    out.assign(transformed_path=out.raw_path, status="ok")[["sample_id", "transformed_path", "status"]].to_csv(
        Path(out_dir) / "crops.csv", index=False)

    print(f"Wrote {len(out)} rows to {Path(out_dir) / 'training.csv'}")
    print(out.groupby(["view", "split", "augmented"]).size().to_string())
    print(f"Cultivars kept: {out.cultivar.nunique()}; dropped: {(~keep).sum()} (see dropped_cultivars.csv)")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-root", type=Path, default=SPLIT_ROOT, help="Folder with train/ and test/.")
    args = parser.parse_args()
    build(args.split_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
