"""Outside + inside photos together: match each view only against the same view, then add the scores per tree."""
import json

import numpy as np

import retrieval_baseline as r


def view_scores(samples, sims, q):
    # Best match per cultivar for photo q, among same-view photos from other trees.
    allowed = (samples.specimen != samples.specimen[q]) & (samples.view == samples.view[q])
    best = {}
    for i in np.where(allowed)[0]:
        c = samples.cultivar[i]
        best[c] = max(best.get(c, -1.0), sims[q, i])
    return best


def main():
    samples = r.load_samples(r.MASKS_CSV)
    embeddings = r.embed(samples, r.RUN_DIR.with_name("retrieval-dinov2-masked") / "embeddings.npz")
    sims = embeddings @ embeddings.T

    results = {"outside_only": [], "inside_only": [], "both": []}
    chance = []
    for specimen, tree in samples.groupby("specimen"):
        if set(tree.view) != {"exterior", "interior"}:
            continue  # this tree needs both an outside and an inside photo
        # Average each view's per-photo scores for this tree.
        per_view = {}
        for view, photos in tree.groupby("view"):
            scores = [view_scores(samples, sims, q) for q in photos.index]
            cultivars = set.intersection(*(set(s) for s in scores))
            per_view[view] = {c: np.mean([s[c] for s in scores]) for c in cultivars}
        # Only rank cultivars that can be matched in both views, so all three methods pick from the same list.
        candidates = set(per_view["exterior"]) & set(per_view["interior"])
        true = tree.cultivar.iloc[0]
        if true not in candidates:
            continue  # no other tree of this cultivar has both views
        both = {c: per_view["exterior"][c] + per_view["interior"][c] for c in candidates}
        for name, scores in [("outside_only", per_view["exterior"]), ("inside_only", per_view["interior"]), ("both", both)]:
            ranked = sorted(candidates, key=lambda c: scores[c], reverse=True)
            results[name].append(ranked.index(true))
        chance.append(len(candidates))

    metrics = {"trees_evaluated": len(chance)}
    for k in (1, 5, 10):
        for name, ranks in results.items():
            metrics[f"{name}_top{k}"] = round(float(np.mean(np.array(ranks) < k)), 4)
        metrics[f"chance_top{k}"] = round(float(np.mean([min(k, n) / n for n in chance])), 4)
    out_dir = r.RUN_DIR.with_name("retrieval-dinov2-masked") / "fusion"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
