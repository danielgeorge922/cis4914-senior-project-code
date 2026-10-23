# Mango cultivar ID: results summary

October 2026. Full details and caveats are in `retrieval_baseline.md`.

## What we built

1. **Labels:** Gemini read the handwritten post-it in each SharePoint photo. Spellings were cleaned (222 → 184 cultivars). 1,386 labeled photos: 751 outside, 635 cut open.
2. **Crop:** OWL-ViT finds the mango in each photo and cuts out the post-it and ruler.
3. **Mask:** the table behind the mango is painted flat gray, so table color can't help matching.
4. **Retrieval (main model):** DINOv2 turns each photo into a vector. A photo is matched to the most similar photos **from other trees**, which gives a ranked shortlist of cultivars. No training needed.
5. **Outside + inside:** for trees with both photos, outside is matched to outside and inside to inside, and the two scores are added.
6. **Gemini reranker:** Gemini sees the photo plus the top 5 candidates (each with a reference photo) and reorders them.

**How we test:** every photo is checked against photos from *other* trees only, so the model has to recognize the cultivar, not the individual tree.

## Results

**Outside photos, all testable cultivars (411 photos, 80 cultivars)**

| | Top-1 | Top-10 |
|---|---|---|
| Our model | **10.7%** | **35.8%** |
| Random guess | 0.55% | 5.5% |

**Outside photos, 20 cultivars with the most trees (181 photos)**

| | Top-1 | Top-10 |
|---|---|---|
| Our model | **26.5%** | **77.3%** |
| Random guess | 5% | 50% |

**Outside + inside photos together (same 179 trees)**

| | Top-1 | Top-5 | Top-10 |
|---|---|---|---|
| Outside only | 11.7% | 26.8% | 39.1% |
| Inside only | 8.9% | 23.5% | 30.7% |
| **Both** | **17.9%** | **35.2%** | **45.8%** |
| Random guess | 0.57% | 2.8% | 5.7% |

**Gemini reranker (`gemini-3.5-flash-lite`, top 5 candidates)**

| Shortlist | Top-1 before | Top-1 after Gemini | Fixed / broke |
|---|---|---|---|
| Outside, 20 cultivars (181 photos) | **26.5%** | 21.5% | 7 / 16 |
| Outside + inside (179 trees) | **17.9%** | 11.7% | 0 / 11 |

## Takeaways

- The model finds a real cultivar signal: **19× better than guessing** at top-1 on outside photos.
- **Adding the cut-open photo helps:** top-1 goes from 11.7% to 17.9% on the same trees.
- **Gemini reranking made it worse** with photos alone. LLMs aren't good at telling plant varieties apart; this matches published results (INQUIRE, arXiv 2411.02537).
- **The numbers are inflated by photo sessions:** matches mostly come from photos taken in the same session (same lighting and setup). When matches are forced across sessions, the model is only ~3× better than guessing.
- **The main limit is the data:** about 2 trees per cultivar, and many cultivars seem to have been photographed in batches.

## Next steps

- Ask the lab whether cultivars were photographed in batches, and collect the same cultivars across different sessions.
- Fill in the cultivar trait sheet (`data/reference/cultivar_traits.json`) and rerun the reranker.
- Hand-check the labels (`data/transformed/review/index.html`).
- Compare against the teammate's ResNet-18 model on the same pipeline.
