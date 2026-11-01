"""Ask Gemini to rerank each photo's top-5 retrieval shortlist."""
import argparse
import base64
import io
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from PIL import Image

ML_ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS = ML_ROOT / "runs/retrieval-dinov2-masked/top20/predictions.csv"
TRAITS = ML_ROOT / "data/reference/cultivar_traits.json"
OUT_DIR = ML_ROOT / "runs/rerank-gemini"
MODEL = "gemini-3.5-flash-lite"
TOP_K = 5  # candidates sent to Gemini
WORKERS = 5  # requests sent at the same time

PROMPT = """The first photo is a mango of unknown cultivar. After it are 5 candidate cultivars, each shown with a
photo of a mango of that cultivar from a different tree. Compare fruit shape, size, skin color, blush, spots and beak.
Rank all 5 candidate names from most to least likely to match the first mango. Use the names exactly as given."""

SCHEMA = {"type": "object", "properties": {"ranking": {"type": "array", "items": {"type": "string"}}},
          "required": ["ranking"]}


def image_part(path):
    image = Image.open(ML_ROOT / path).convert("RGB")
    image.thumbnail((512, 512))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90)
    return {"type": "image", "data": base64.b64encode(buffer.getvalue()).decode(), "mime_type": "image/jpeg"}


def ask_gemini(client, row, traits):
    candidates = json.loads(row.candidates)[:TOP_K]
    parts = [{"type": "text", "text": PROMPT}, image_part(row.query)]
    for i, candidate in enumerate(candidates, 1):
        text = f"Candidate {i}: {candidate['cultivar']}"
        known = {k: v for k, v in traits.get(candidate["cultivar"], {}).items() if v is not None}
        if known:
            text += f". Known traits: {json.dumps(known)}"
        parts += [{"type": "text", "text": text}, image_part(candidate["photo"])]

    # Gemini sometimes answers "busy" (503) or "slow down" (429); wait and try again.
    for attempt in range(1, 6):
        try:
            response = client.interactions.create(
                model=MODEL, input=parts, store=False,
                response_format={"type": "text", "mime_type": "application/json", "schema": SCHEMA},
            )
            break
        except Exception as error:
            if getattr(error, "status_code", None) not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
            print(f"Gemini busy, retrying in {30 * attempt}s", flush=True)
            time.sleep(30 * attempt)
    ranking = json.loads(response.output_text)["ranking"]
    # Keep Gemini's order for valid names, then add any it left out in retrieval order.
    names = [c["cultivar"] for c in candidates]
    ranking = [n for n in dict.fromkeys(ranking) if n in names]
    return ranking + [n for n in names if n not in ranking]


def rerank(predictions_path=PREDICTIONS, out_dir=OUT_DIR, limit=None):
    load_dotenv(ML_ROOT.parent / ".env")
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY in the repository-root .env")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    traits = json.loads(TRAITS.read_text())
    rows = pd.read_csv(predictions_path)
    if limit:
        rows = rows.head(limit)

    # Answers are saved as we go, so a rerun skips photos already done.
    out_dir.mkdir(parents=True, exist_ok=True)
    answers_path = out_dir / "answers.jsonl"
    answers = {}
    if answers_path.exists():
        for line in answers_path.read_text().splitlines():
            answer = json.loads(line)
            answers[answer["query"]] = answer["ranking"]
    todo = [row for row in rows.itertuples() if row.query not in answers]
    with answers_path.open("a") as file, ThreadPoolExecutor(WORKERS) as pool:
        rankings = pool.map(lambda row: ask_gemini(client, row, traits), todo)
        for i, (row, ranking) in enumerate(zip(todo, rankings), 1):
            answers[row.query] = ranking
            file.write(json.dumps({"query": row.query, "ranking": ranking}) + "\n")
            file.flush()
            print(f"{i}/{len(todo)}", flush=True)

    results = []
    for row in rows.itertuples():
        before = [c["cultivar"] for c in json.loads(row.candidates)][:TOP_K]
        after = answers[row.query]
        results.append({"retrieval_top1": before[0] == row.true, "rerank_top1": after[0] == row.true,
                        "retrieval_top3": row.true in before[:3], "rerank_top3": row.true in after[:3],
                        "true_in_shortlist": row.true in before})
    results = pd.DataFrame(results)
    metrics = {"queries": len(results), **{k: round(float(results[k].mean()), 4) for k in results},
               "fixed": int((~results.retrieval_top1 & results.rerank_top1).sum()),
               "broken": int((results.retrieval_top1 & ~results.rerank_top1).sum())}
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="Only rerank the first N photos.")
    args = parser.parse_args()
    rerank(limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
