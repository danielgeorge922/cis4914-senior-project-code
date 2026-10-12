"""Build the V1 training manifest: exterior SharePoint photos with normalized cultivar labels and specimen groups."""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

ML_ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS = ML_ROOT / "data/manifests/sharepoint_gemini/annotations.jsonl"
OUT_DIR = ML_ROOT / "data/manifests/sharepoint_v1"


def normalize(value):
    # Same rule as the audit notebook: collapse whitespace, strip, uppercase.
    if pd.isna(value):
        return pd.NA
    text = re.sub(r"\s+", " ", str(value)).strip().upper()
    return text or pd.NA


def build(annotations=ANNOTATIONS, out_dir=OUT_DIR):
    with Path(annotations).open(encoding="utf-8") as handle:
        df = pd.json_normalize([json.loads(line) for line in handle if line.strip()])
    aliases = pd.read_csv(Path(out_dir) / "cultivar_aliases.csv")
    alias_map = dict(zip(aliases.raw.map(normalize), aliases.canonical.map(normalize)))

    df["cultivar_raw"] = df["annotation.cultivar"]
    df["cultivar"] = df["annotation.cultivar"].map(normalize)
    df["cultivar"] = df["cultivar"].map(lambda c: alias_map.get(c, c) if pd.notna(c) else c)
    df = df[df["cultivar"].notna() & df["annotation.view_type"].eq("exterior")].copy()

    # Specimen codes are grouped per cultivar (as in the notebook); photos without a code are their own group.
    code = df["annotation.specimen_code"].astype("string").str.replace(r"\s+", "", regex=True).str.upper()
    df["specimen"] = (df["cultivar"] + "|" + code).where(code.notna() & code.ne(""), "PHOTO|" + df["raw_path"])
    df["sample_id"] = df["raw_path"].map(lambda p: Path(p).stem)

    out = df[["sample_id", "raw_path", "sha256", "cultivar_raw", "cultivar", "specimen"]].sort_values("sample_id")
    out_path = Path(out_dir) / "training.csv"
    out.to_csv(out_path, index=False)

    specimens = out.groupby("cultivar")["specimen"].nunique()
    print(f"Wrote {len(out)} rows to {out_path.relative_to(ML_ROOT)}")
    print(f"Classes: {out.cultivar.nunique()}; median photos/class: {out.cultivar.value_counts().median():g}")
    print(f"Cultivars with >=2 specimens (testable): {specimens.ge(2).sum()}; >=4 specimens: {specimens.ge(4).sum()}")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=ANNOTATIONS)
    args = parser.parse_args()
    build(args.annotations)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
