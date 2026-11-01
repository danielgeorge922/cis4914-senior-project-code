"""Make an HTML page to check every labeled photo by eye: original (with the post-it), crop, and labels."""
import html
from pathlib import Path

import pandas as pd
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()
ML_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ML_ROOT / "data/transformed/review"


def main():
    rows = pd.read_csv(ML_ROOT / "data/manifests/sharepoint_v1/training.csv")
    crops = pd.read_csv(ML_ROOT / "data/manifests/sharepoint_v1/crops.csv")
    rows = rows.merge(crops[["sample_id", "transformed_path", "status"]], on="sample_id", how="left")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sections = []
    for cultivar, group in rows.groupby("cultivar"):
        cards = []
        for row in group.itertuples():
            preview = OUT_DIR / f"{row.sample_id}.jpg"
            if not preview.exists():
                image = ImageOps.exif_transpose(Image.open(ML_ROOT / row.raw_path)).convert("RGB")
                image.thumbnail((800, 800))
                image.save(preview, quality=80)
            crop = f"../../../{row.transformed_path}" if isinstance(row.transformed_path, str) else ""
            cards.append(f"""<div class="card"><img src="{preview.name}"><img src="{crop}">
<p><b>{html.escape(row.sample_id)}</b> · tree {html.escape(row.specimen.split('|')[-1][-20:])} · crop {row.status}<br>
Gemini read: {html.escape(str(row.cultivar_raw))}</p></div>""")
        sections.append(f"<h2>{html.escape(cultivar)} ({len(group)} photos)</h2>" + "".join(cards))

    page = OUT_DIR / "index.html"
    page.write_text(f"""<html><head><meta charset="utf-8"><title>Label review</title><style>
body {{ font-family: sans-serif; margin: 16px; }} .card {{ display: inline-block; width: 420px; margin: 6px;
vertical-align: top; border: 1px solid #ccc; padding: 6px; }} .card img {{ width: 200px; height: 200px;
object-fit: contain; background: #eee; }} p {{ margin: 4px 0; font-size: 13px; }}
</style></head><body><h1>Label review: {len(rows)} photos, {rows.cultivar.nunique()} cultivars</h1>
{"".join(sections)}</body></html>""", encoding="utf-8")
    print(f"Open {page}")


if __name__ == "__main__":
    main()
