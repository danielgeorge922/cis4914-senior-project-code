"""Train classifiers on the split_v1 manifest for one view, then write and score each run's validation shortlist.

Uses the GPU when there is one. Test is left alone until the final comparison.

On Colab (Runtime > Change runtime type > GPU):
    1. Locally, zip split_full/ and ml-models/data/manifests/split_v1/ and upload both zips to Google Drive.
    2. In a Colab cell:
        from google.colab import drive; drive.mount("/content/drive")
        !git clone -b demo/COIL https://github.com/danielgeorge922/cis4914-senior-project-code.git /content/repo
        !unzip -q /content/drive/MyDrive/split_full.zip -d /content/repo
        !unzip -q /content/drive/MyDrive/split_v1.zip -d /content/repo/ml-models/data/manifests
        %cd /content/repo/ml-models
        !python scripts/train_split_v1.py --view exterior
        !python scripts/train_split_v1.py --view leaf
    3. Copy runs/split_v1/ back to Drive before the session ends.
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd

from classifier_shortlist import write_shortlist
from mango_transfer import ARCHITECTURES, fit_experiment, prepare_split_v1, save_run
from report_shortlist import report

ML_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ML_ROOT / "data/manifests/split_v1/training.csv"
RUNS = ML_ROOT / "runs/split_v1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", required=True, help="exterior or leaf.")
    parser.add_argument("--architectures", nargs="+", default=list(ARCHITECTURES))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()

    exp = prepare_split_v1(args.manifest, ML_ROOT, args.view)
    print({split: len(rows) for split, rows in exp["splits"].items()}, f"{len(exp['class_names'])} cultivars")
    for architecture in args.architectures:
        result = fit_experiment(exp, architecture, epochs=args.epochs, batch_size=args.batch_size,
                                num_workers=args.num_workers)
        model = result.pop("model")
        size_mb = sum(p.numel() * p.element_size() for p in model.parameters()) / 1e6
        run_dir = save_run(result, exp, f"split_v1_{args.view}", RUNS, args.manifest)

        started = time.perf_counter()
        shortlist = write_shortlist(run_dir, run_dir / "val_shortlist.csv", split="validation",
                                    num_workers=args.num_workers)
        seconds = time.perf_counter() - started
        metrics, per_class, confusion = report(shortlist)
        # Includes loading the run and reading photos, so it's an upper bound on inference time.
        metrics |= {"model_size_mb": round(size_mb, 1),
                    "ms_per_photo_with_loading": round(1000 * seconds / metrics["images"], 1)}
        (run_dir / "val_metrics.json").write_text(json.dumps(metrics, indent=2))
        per_class[per_class.support > 0].to_csv(run_dir / "val_per_class.csv", index=False)
        names = per_class.class_name.tolist()
        pd.DataFrame(confusion.numpy(), index=names, columns=names).to_csv(run_dir / "val_confusion.csv")
        print(run_dir, json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
