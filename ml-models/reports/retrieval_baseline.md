# Retrieval baseline: frozen DINOv2 features on SharePoint mango photos

*October 9, 2026. First honest accuracy number for mango cultivar ID.*

## TL;DR

# Crop fruit.py
Use owl vit model to dynamically crop  images and focus on the mango with padding. OWL VIT is a dynamic prompt object detection model that can give pixel boundaries for prompts. This is saved in `data/transformed/sharepoint_v1/` (boxes and scores in `data/manifests/sharepoint_v1/crops.csv`). 


# mask background.py
Mask refers to marking the non-mango part of the image, even if cropped, as gray. This way a black table background vs a white one doesn't lead to variance. 
The script applies a known masking otsu algorithm to analyze the average pixel differences. Assuming the corners of the image represent the background table color, the algorithm marks any pixels with a RGB difference less than a certain amount as being part of the table, and to be masked over. Anotehr loop comes by and fills in certain small boundaries of the opposite mask within a greater region. This is saved in `data/transformed/sharepoint_v1_masked/` (status in `data/manifests/sharepoint_v1/masks.csv`)

# build manifest
It organizes cropped and/or masked images with original labels as the original jupyter notebook did. Note that, a spell check is applied to Gemini's hand-read labels according to Claude's knowledge of mango varieties' proper spelling. It saves images in `data/manifests/sharepoint_v1/training.csv`

# retrieval baseline.py
It fetches pre-processed images, and runs an embedding algorithm using Meta's's DinoV2 Computer Vision model. This embedding algorithm represents a vector description of the image according to the model, which we have not fine tuned. Since we are currently building a retrieval model, the similarity metric between any two images will be the dot product of its vectors embeddings, where 1 = same, and 0 = share nothing in common. 

Thus for every image in our sample, we track its embedding similarity between it and the rest of the dataset to find the closest mango variety. This represents our model evaluation, note that for a given image's evaluation, we exclude images from that same individual tree to make sure we are identifying mango varieties, and not individuals/


We track a confusion matrix, how often a given mango variety is confused with another one. We also track our success rate for identifying the correct mango variety in the top-10 of candidates, as well as top-1 (a correct guess).


### Notes
1. We have a ~20 cultivar (mango variety) subset with 5+ images. Testing on this subset shows how our model performs when it has at least a certain amount of image data.

For this 20 variety run, the top 10 accuracy percentage (ie, including the correct variety in the top10 most similar list) is 77%, and the top-1 accuracy is 26%. These are not stellar features, but they are 1.5 and 5x better than a chance guess respectively

2. We also need to build an LLm reranker using the top 10 list. We can attach our confusion matrix as part of LLM context to show our model which mango varieties are often confused with each other.

3. We overalll need to refine our pre-processing and ensure it is optimal, think of new and better architectures for our use case, and find more data if possible







# LLM SUmmary


- Frozen DINOv2 + nearest-neighbor retrieval finds a **real but weak** cultivar signal in the SharePoint photos.
- Headline (background masked, all testable cultivars): **top-1 10.7% vs 0.55% chance (~19×), top-10 35.8% vs 5.5% (~6.5×).**
- **These numbers are inflated by photo-session effects.** A query's best match comes from the same photo setup 92% of the time, against 51% expected by chance. When matches are only allowed across sessions, the model is just **~2–3× better than chance.**
- The main problem is not just low data. Cultivars appear to have been **photographed in batches**, so any model trained on this data can learn the session instead of the cultivar.

---

## 1. Goal

Get a first, honest number for how well an image model can identify mango cultivars from the existing SharePoint lab photos, using the approach best suited to how little data we have. This number is the baseline every later idea has to beat: a linear probe, a different backbone, the LLM reranker.

## 2. Approaches considered

| Approach | What it is | Fit for our data | Decision |
|---|---|---|---|
| **Transfer-learning classifier** (original plan in `context.md`) | Pretrained backbone, partly or fully retrained, with a new 222-way head | Poor. Highly sensitive to settings, and it overfits with ~2 specimens per cultivar | Deferred |
| **Linear probe** | Frozen features plus a trained logistic regression | OK, but weak at 1–3 examples per class (CLIP and CoOp papers) | Deferred; it's the stable comparison point |
| **Retrieval (chosen)** | Frozen features; match each query photo to the most similar stored photos | Best fit. No training, deterministic, and it gives the top-k list plus the matching photos an LLM reranker would need | **Built** |
| Retrieval + probe blend | Average the two score lists | Usually at least as good as either alone (Jia et al. 2021; Long et al. 2022) | Next experiment |
| Multimodal LLM reranker | An LLM reranks the top-10 using the photo, reference photos and a cultivar trait store | Promising, but the best published fit, INQUIRE, showed LLM reranking **barely helped on species ID** | Needs a strong stage-1 shortlist first |

Key references:
- RAR, arXiv 2403.13805: retrieval → multimodal LLM ranking on fine-grained, few-shot recognition. The closest match to our plan.
- INQUIRE, arXiv 2411.02537: CLIP retrieval → VLM rerank. On species queries BioCLIP scored 44.8 and GPT-4o 44.3.
- Jia et al., "Rethinking Nearest Neighbors", arXiv 2112.08459: kNN is competitive with a linear classifier and helps most in low-data regimes.
- Tip-Adapter, arXiv 2207.09519: training-free retrieval matches trained few-shot methods.
- Finer, arXiv 2402.16315; Zhang et al., arXiv 2405.18415: LLMs alone are bad at fine-grained ID, so a first-stage vision model is needed.

Data sources considered:
- **SharePoint lab photos: used.** Real fruit, consistent setup, specimen codes available for honest splits.
- **Hugging Face `earl562/mango-varieties`: not used.** 82% of it comes from a forum. A random sample of 12 images had only ~2 usable single-fruit photos, and many labels are junk ("Sulfur", "These", "2020"). It overlaps with only 64 of our cultivars. Revisit only after a 100-image audit.

## 3. Data

Source: the Gemini transcriptions of the handwritten post-it labels (`data/manifests/sharepoint_gemini/annotations.jsonl`). These are **draft labels, not yet human-reviewed.**

| | Count |
|---|---|
| Photos annotated | 1,408 (762 exterior, 645 interior, 1 unknown) |
| Exterior photos with a cultivar | 751 |
| Cultivars after spelling merges | 184 |
| Median photos per cultivar | 3 |
| Cultivars with ≥2 specimens (testable) | 81 |
| Cultivars with ≥4 specimens | 12 |

A **specimen** is the post-it's specimen code (e.g. "R11 P7", probably row/plant), grouped per cultivar. A photo without a code counts as its own specimen. Cultivars with only one specimen **can't be tested honestly**, because their only reference photos come from the very specimen being queried.

## 4. Preprocessing

All steps are scripts in `ml-models/scripts/`, run from `ml-models/` with `uv run python scripts/<name>.py`. Raw photos are only ever read; all outputs go to new folders.

1. **Clean names → training list** (`build_manifest.py`)
   - Normalize labels as the audit notebook does (trim, collapse spaces, uppercase).
   - Apply `data/manifests/sharepoint_v1/cultivar_aliases.csv`. That's the notebook's 28 spelling merges plus 8 clear-cut ones added here: Juliett/Juliette, Besenara/Bessenara, Mabruka/Mabrouka, Maha Schanook/Maha Chanok, Pram Kai Mea/Mai, Rock Saigon/Rockdale Saigon, Stringles/Stringless Peach, Torpentine/Turpentine.
   - **Left unmerged because they're ambiguous:** the "MF-" prefixes, Mong Tong vs 9822 Mon Tong, Keitt vs Kent, 9816 vs 9819.
   - Keep exterior photos with a cultivar. Output: `data/manifests/sharepoint_v1/training.csv`.
2. **Crop out the post-it card and ruler** (`crop_fruit.py`). The card has the cultivar name handwritten on it, so without cropping a model could read the answer.
   - Decode the HEIC and fix orientation.
   - Run zero-shot detection with the prompt "a mango fruit", take the best box, and pad it 10%.
   - The detector was switched from OWLv2 (~9 s per photo on CPU) to **OWL-ViT v1 base** (~2 s per photo).
   - Result: 735 OK, 16 low-confidence (excluded). Output: `data/transformed/sharepoint_v1/`, `crops.csv`, `_contact_sheet.jpg`.
   - Note: some fruits have **numbers written on the skin in marker.** They're probably fruit numbers within a specimen, and leave-one-specimen-out limits their effect.
3. **Mask the background** (`mask_background.py`). The tables differ: about 42% light gray, about 58% dark navy or black.
   - Estimate each photo's table color from its border pixels.
   - Keep pixels whose color is far from it (Otsu threshold), clean up the mask, and fill holes.
   - Replace the background with one flat gray (the ImageNet mean).
   - 735 masked, 0 failures. Output: `data/transformed/sharepoint_v1_masked/`, `masks.csv`, `_contact_sheet.jpg`.

## 5. Model and evaluation

`retrieval_baseline.py`:

- **Features:** DINOv2 ViT-B/14 (`facebook/dinov2-base`, from Hugging Face), **frozen**. Standard processor (resize, center crop to 224, ImageNet normalization). The CLS/pooled embedding (768-d) is L2-normalized. Embeddings are cached in `runs/<run>/embeddings.npz`.
- **Retrieval:** cosine similarity. Each cultivar's score is its **single best match** among the reference photos, so cultivars with more photos don't win by count.
- **Evaluation: leave-one-specimen-out.** A query may only match photos from *other* specimens. Queries whose cultivar has no other specimen are skipped.
- **Metrics:** top-1, top-5 and top-10, each next to chance (k ÷ number of candidate cultivars); per-cultivar average top-1; most-confused pairs.
- **Options:**
  - `--masked` uses the background-masked images.
  - `--top-classes 20` restricts queries and references to the 20 cultivars with the most distinct specimens.

## 6. Results

| Run | Queries / cultivars | Top-1 | Top-5 | Top-10 |
|---|---|---|---|---|
| Cropped, all | 411 / 80 | 12.6% | 29.2% | 37.5% |
| **Masked, all** | 411 / 80 | **10.7%** | **25.6%** | **35.8%** |
| Chance (all) | | 0.55% | 2.7% | 5.5% |
| Cropped, 20-way subset | 181 / 20 | 26.5% | 56.9% | 80.1% |
| **Masked, 20-way subset** | 181 / 20 | **26.5%** | **58.6%** | **77.3%** |
| Chance (20-way) | | 5% | 25% | 50% |

Results are in `runs/retrieval-dinov2/` and `runs/retrieval-dinov2-masked/` (`metrics.json`, `predictions.csv`, and `top20/` subfolders). The 20-way subset is easier than the full task and is **not** the headline number.

### Photo-session check

| Run | Best match comes from the same table setup | Expected by chance |
|---|---|---|
| Cropped | 97% (93% on the 20-way subset) | 51% |
| Masked | 92% (87% on the 20-way subset) | 51% |

When the best match came from a different setup, top-1 was 0% in the cropped runs. Masking the table pixels barely helped: the session still leaks through **lighting, white balance and exposure on the fruit itself.**

### Cross-session floor

Here a query may only match photos taken on the *other* table setup. File: `runs/retrieval-dinov2-masked/cross_session_metrics.json`.

| | Queries | Top-1 | Top-5 | Top-10 |
|---|---|---|---|---|
| All cultivars | 147 | 3.4% (chance 1.0%, ~3×) | 16.3% (5.1%) | 26.5% (10.3%, ~2.6×) |
| 20-way subset | 96 | 11.5% (chance 6.5%, ~1.8×) | 40.6% (32.6%) | 61.5% (65.3%, **≈ chance**) |

The samples are small, so these are noisy: 3.4% top-1 is about 5 correct out of 147.

### Most confused pairs (masked)

- Saigon ↔ Bullock's Heart
- Young → Duncan
- Benett Alphonso → Duncan / Saigon / Angie
- Ruby → Irwin
- Seedling → Palmer
- Edward → Ono
- Glazier → Miami Late

## 7. Conclusions

1. **There is a real cultivar signal, but it's weak.** Even across sessions the model beats chance by ~2–3× on the full task.
2. **The headline accuracy (10–27% top-1) is inflated by photo-session effects.** The truth lies between the cross-session floor and the masked numbers.
3. **The bottleneck is the data, not just the model:**
   - Cultivars seem to have been photographed in batches on different setups, so more photos *of the same kind* won't fix it.
   - About 2 specimens per cultivar, and 102 of 184 cultivars from a single specimen, which can't be tested.
4. **An LLM reranker isn't justified yet.** The stage-1 shortlist is too weak across sessions, and published evidence (INQUIRE) shows little reranking gain on species-level ID.

## 8. Next steps

**Cheap, with no new photos:**
1. **White-balance and exposure correction** using each photo's neutral table as a reference, applied before masking. This targets the session cast directly.
2. **Backbone comparison** using the embedding cache: BioCLIP 2, DINOv2-Large, DINOv3 (check its custom license before deploying).
3. **Specimen-level matching:** average each specimen's photos, including the interior ones, and compare specimen to specimen.
4. Linear probe and retrieval + probe blend, as the stable comparison.

**Add fruit size, using the same raw photos and no re-cropping:**
- The crop step threw nothing away. The raw photos still contain the ruler and post-it, and `crops.csv` stores each fruit's box in original-photo pixels (before the 10% padding).
- A separate step (e.g. `measure_fruit.py`) could:
  1. Detect "a ruler" (or "a sticky note") on each raw photo with the same OWL-ViT detector.
  2. Turn it into a pixels-per-cm scale. Ruler ticks are the most accurate; a standard ~7.6 cm post-it is a rougher fallback.
  3. Divide the fruit box, or better the fruit mask, by that scale to get length, width and area in cm.
  4. Write a `sizes.csv`.
- Those sizes plug straight into the server's `apply_ranges` measurement filter, or into the reranker's trait store. The mango genetics paper reports fruit weight from under 50 g to over 2,000 g, so size should help separate cultivars.
- Caveat: this assumes the ruler sits at roughly the same distance from the camera as the fruit. Reliably reading ruler ticks is the fiddly part.

**Data augmentation ideas:**
- **Test-time augmentation (works with frozen retrieval now):** average each photo's embedding over flips and rotations, so matches don't depend on how a fruit was laid down.
- **Augmented reference photos:** store flipped and rotated copies of each reference photo, so each cultivar has more views to match against.
- **Background swapping:** paste each masked fruit onto every table color (gray, black, navy) and onto textured backgrounds. That breaks the link between session and background, and it's the main augmentation if a model is ever trained.
- **Lighting and exposure jitter, not hue jitter:** randomly shift brightness, exposure and mild white balance to imitate other sessions. **Avoid strong color or hue jitter.** Skin color and blush are real cultivar traits, so heavy color augmentation erases the signal.
- **Geometric augmentation, if training later:** any rotation (fruit lie on a table, so there's no "up"), flips, scale and crop jitter, and mild blur for phone-photo realism.
- **More views per specimen:** combine each specimen's exterior and cut-open (interior) photos into one specimen-level example instead of separate unrelated photos.
- **Never augment across the train/test split.** Augmented copies of a specimen stay with that specimen, or the test leaks.

**Needs the lab or advisors:**
- Confirm whether cultivars were photographed in batches, and get the session dates or setups.
- Get the official cultivar/accession list to replace the guessed spelling merges.
- Collect the same cultivars across **different sessions and setups**. This is the real fix.
- Human review of the Gemini labels, starting with the most-confused pairs.

## 9. Reproduce

Run from `ml-models/` on CPU (~1 hour total, mostly cropping). Photos must be in `data/raw/sharepoint_data/Fruit_Images/`.

```bash
uv run python scripts/build_manifest.py
uv run python scripts/crop_fruit.py --min-score 0.1
uv run python scripts/mask_background.py
uv run python scripts/retrieval_baseline.py --masked
uv run python scripts/retrieval_baseline.py --masked --top-classes 20
```

The cross-session numbers came from a one-off analysis and aren't wired into a script yet. Dependency added: `transformers`, in `pyproject.toml` / `uv.lock`.
