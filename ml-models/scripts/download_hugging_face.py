import argparse
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import snapshot_download

ML_ROOT = Path(__file__).resolve().parents[1]
DATASET = "earl562/mango-varieties"
REVISION = "f482454c26bcab8137b0eed3e45317e8bf6ff260"
DEFAULT_OUTPUT = ML_ROOT / "data/raw/hugging_face_data"


def download(output=DEFAULT_OUTPUT, splits=None):
    load_dotenv(ML_ROOT.parent / ".env")
    output = Path(output).resolve()
    patterns = None
    if splits:
        patterns = ["README.md", ".gitattributes", *[f"data/{split}-*.parquet" for split in splits]]
    print(f"Downloading {DATASET}@{REVISION} to {output}", flush=True)
    snapshot_download(
        repo_id=DATASET,
        repo_type="dataset",
        revision=REVISION,
        local_dir=output,
        allow_patterns=patterns,
        max_workers=4,
    )
    print("Download complete. Raw Parquet files preserve images, labels, and source metadata.")


def main():
    parser = argparse.ArgumentParser(description="Download the team's pinned mango dataset from Hugging Face.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--split", action="append", choices=["train", "validation", "test"],
                        help="Download only this split; repeat for multiple splits. Default: all.")
    args = parser.parse_args()
    try:
        download(args.output, args.split)
    except KeyboardInterrupt:
        print("\nInterrupted. Rerun the same command to continue downloading.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
