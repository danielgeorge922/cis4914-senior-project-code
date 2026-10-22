"""Frozen DINOv2 features + nearest-neighbor retrieval, evaluated leave-one-specimen-out."""
import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

ML_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = (ML_ROOT / "data/raw").resolve()
MANIFEST = ML_ROOT / "data/manifests/sharepoint_v1/training.csv"
CROPS_CSV = ML_ROOT / "data/manifests/sharepoint_v1/crops.csv"
MASKS_CSV = ML_ROOT / "data/manifests/sharepoint_v1/masks.csv"
RUN_DIR = ML_ROOT / "runs/retrieval-dinov2"
MODEL = "facebook/dinov2-base"


def safe_output(path):
    path = Path(path).resolve()
    if path.is_relative_to(RAW_ROOT):
        raise RuntimeError(f"Refusing to write inside raw data: {path}")
    return path


def load_samples(images_csv=CROPS_CSV):
    crops = pd.read_csv(images_csv)
    samples = pd.read_csv(MANIFEST).merge(crops[crops.status.eq("ok")], on="sample_id")
    return samples.reset_index(drop=True)

# retrieval models work by mapping by similairty so we store embedding vector descriptions of images and compare by dot ptoduct similariy
def embed(samples, cache, batch_size=16):
    # Cached by sample_id, so reruns only embed new crops.
    cached = {}
    if cache.exists():
        data = np.load(cache, allow_pickle=False)
        cached = dict(zip(data["sample_id"], data["embedding"]))
    missing = [s for s in samples.sample_id if s not in cached]
    if missing:
        processor = AutoImageProcessor.from_pretrained(MODEL)
        model = AutoModel.from_pretrained(MODEL).eval()
        paths = samples.set_index("sample_id").transformed_path
        for start in range(0, len(missing), batch_size):
            ids = missing[start:start + batch_size]
            images = [Image.open(ML_ROOT / paths[i]).convert("RGB") for i in ids]
            with torch.no_grad():
                cls = model(**processor(images=images, return_tensors="pt")).pooler_output
            for i, vector in zip(ids, torch.nn.functional.normalize(cls, dim=1).numpy()):
                cached[i] = vector
            print(f"embedded {min(start + batch_size, len(missing))}/{len(missing)}", flush=True)
        safe_output(cache).parent.mkdir(parents=True, exist_ok=True)
        np.savez(safe_output(cache), sample_id=np.array(list(cached)), embedding=np.stack(list(cached.values())))
    return np.stack([cached[s] for s in samples.sample_id])


def top_classes(samples, n):
    # Most distinct specimens first; ties broken by photo count.
    stats = samples.groupby("cultivar").agg(specimens=("specimen", "nunique"), photos=("sample_id", "size"))
    return stats.sort_values(["specimens", "photos"], ascending=False).head(n)


def evaluate(samples, embeddings, out_dir, ks=(1, 5, 10)):
    labels = samples.cultivar.to_numpy()
    specimens = samples.specimen.to_numpy()
    classes = np.unique(labels)
    sims = embeddings @ embeddings.T

    rows, hits, chance = [], {k: [] for k in ks}, {k: [] for k in ks}
    for q in range(len(samples)):
        gallery = specimens != specimens[q]
        # Each cultivar's score is its single best match among photos from other specimens.
        scores = {c: sims[q, gallery & (labels == c)].max() for c in classes if (gallery & (labels == c)).any()}
        if labels[q] not in scores:
            continue  # cultivar has no other specimen: not testable
        ranked = sorted(scores, key=scores.get, reverse=True)
        rank = ranked.index(labels[q])
        for k in ks:
            hits[k].append(rank < k)
            chance[k].append(min(k, len(ranked)) / len(ranked))
        best = np.where(gallery)[0][sims[q, gallery].argmax()]
        # Each shortlisted cultivar with its best-matching photo from another tree (reference for the reranker).
        candidates = []
        for c in ranked[:10]:
            allowed = np.where(gallery & (labels == c))[0]
            match = allowed[sims[q, allowed].argmax()]
            candidates.append({"cultivar": c, "score": round(float(scores[c]), 4),
                               "photo": samples.transformed_path[match]})
        rows.append({"query": samples.transformed_path[q], "true": labels[q], "rank": rank + 1,
                     "top10": "; ".join(f"{c} ({scores[c]:.3f})" for c in ranked[:10]),
                     "best_match": samples.transformed_path[best], "best_match_cultivar": labels[best],
                     "candidates": json.dumps(candidates)})

    predictions = pd.DataFrame(rows)
    predictions["pred"] = predictions.top10.str.split(" \\(").str[0]
    per_class = predictions.assign(hit=predictions["rank"].eq(1)).groupby("true").hit.mean()
    confused = Counter(zip(predictions.true, predictions.pred))
    confused = [{"true": t, "predicted": p, "count": n} for (t, p), n in confused.most_common() if t != p][:20]
    metrics = {
        "queries_evaluated": len(predictions),
        "queries_skipped": len(samples) - len(predictions),
        "cultivars_testable": int(predictions.true.nunique()),
        "cultivars_in_gallery": int(len(classes)),
        **{f"top{k}": round(float(np.mean(hits[k])), 4) for k in ks},
        **{f"top{k}_chance": round(float(np.mean(chance[k])), 4) for k in ks},
        "top1_macro": round(float(per_class.mean()), 4),
        "most_confused": confused,
    }
    out_dir = safe_output(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions.drop(columns="pred").to_csv(out_dir / "predictions.csv", index=False)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-classes", type=int, help="Restrict queries and gallery to the N most-specimen cultivars.")
    parser.add_argument("--masked", action="store_true", help="Use background-masked crops (scripts/mask_background.py).")
    parser.add_argument("--rerank", action="store_true", help="Then rerank each top-10 with Gemini (scripts/rerank_gemini.py).")
    args = parser.parse_args()

    run_dir = RUN_DIR.with_name(RUN_DIR.name + "-masked") if args.masked else RUN_DIR
    samples = load_samples(MASKS_CSV if args.masked else CROPS_CSV)
    samples = samples[samples.view.eq("exterior")].reset_index(drop=True)
    embeddings = embed(samples, run_dir / "embeddings.npz")
    out_dir = run_dir
    if args.top_classes:
        chosen = top_classes(samples, args.top_classes)
        print(f"{args.top_classes}-way subset (cultivar: specimens, photos):")
        print(chosen.to_string())
        keep = samples.cultivar.isin(chosen.index).to_numpy()
        samples, embeddings = samples[keep].reset_index(drop=True), embeddings[keep]
        out_dir = run_dir / f"top{args.top_classes}"

    metrics = evaluate(samples, embeddings, out_dir)
    print(json.dumps({k: v for k, v in metrics.items() if k != "most_confused"}, indent=2))
    print("Most confused (true -> predicted, count):")
    for pair in metrics["most_confused"][:10]:
        print(f"  {pair['true']} -> {pair['predicted']}: {pair['count']}")

    if args.rerank:
        from rerank_gemini import rerank
        rerank(out_dir / "predictions.csv", out_dir / "rerank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
