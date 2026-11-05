"""Score any shortlist CSV (query, true, shortlist) with mango_transfer's classification_metrics.

Pass --answers to score the reranked order from rerank_gemini.py instead.
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import torch

from mango_transfer import classification_metrics


def report(shortlist_csv, answers=None):
    rows = pd.read_csv(shortlist_csv)
    shortlists = [json.loads(s) for s in rows.shortlist]
    reranked = {}
    if answers:
        for line in Path(answers).read_text().splitlines():
            answer = json.loads(line)
            reranked[answer["query"]] = answer["ranking"]
    names = sorted(set(rows.true) | {n for s in shortlists for n in s})
    # Cultivars not on a photo's shortlist all tie for last, so top-k only means something up to the shortlist length.
    scores = torch.full((len(rows), len(names)), -1e9)
    for i, (query, shortlist) in enumerate(zip(rows["query"], shortlists)):
        top = reranked.get(query, [])
        ranking = top + [n for n in shortlist if n not in top]
        for rank, name in enumerate(ranking):
            scores[i, names.index(name)] = -rank
    labels = torch.tensor([names.index(t) for t in rows.true])
    return classification_metrics(labels, scores, names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("shortlist_csv", type=Path)
    parser.add_argument("--answers", type=Path, help="answers.jsonl from rerank_gemini.py.")
    parser.add_argument("--out", type=Path, help="Folder for report_metrics.json and report_per_class.csv.")
    args = parser.parse_args()
    metrics, per_class, _ = report(args.shortlist_csv, args.answers)
    print(json.dumps(metrics, indent=2))
    out = args.out or args.shortlist_csv.parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "report_metrics.json").write_text(json.dumps(metrics, indent=2))
    per_class[per_class.support > 0].to_csv(out / "report_per_class.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
