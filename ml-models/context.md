# ML Models Working Context

This file is the living handoff for the mango data and modeling work. Update it when the data contract, commands, or preprocessing decisions change.

## Four-model JPEG workflow (2026-10-11)

The active notebook is `notebooks/inital_models.ipynb`. Its final **Four transfer-learning experiments** section uses `scripts/mango_transfer.py` and the JPEG manifest at `data/manifests/sharepoint_jpg/annotations.jsonl`. Existing raw images and the original Gemini manifest remain the provenance source. Labels use capitalization/whitespace normalization only; spelling aliases are not merged.

The user requested two benchmarks per view. `interior_3plus` has 24 classes/163 images, `exterior_3plus` 24/191: these require both >=4 images and >=3 global code/hash-connected groups per class. They share a joint group assignment across views, preserve every selected class in all three splits, and keep groups with unknown codes in training. Counts alone do not guarantee group-split feasibility; the implementation verifies actual coverage and stops if a valid assignment cannot be found.

`interior_4plus` has 59 classes/325 images and `exterior_4plus` 78/470. The user explicitly chose individual-image stratification with every class in every split, accepting and reporting related-code overlap. Exact duplicates remain together. These broader splits have 69 interior and 102 exterior code groups crossing splits, so their scores may be optimistic. Targets are 60/20/20; actual train/validation/test image counts are 87/34/42 (interior_3plus), 185/70/70 (interior_4plus), 105/41/45 (exterior_3plus), and 268/101/101 (exterior_4plus), seed 4914.

The shared factory supports ImageNet V1 ResNet50, VGG16, and EfficientNetB0 for all four experiments (12 configurations). Backbones and BatchNorm statistics stay frozen, pooled features feed dropout/Linear(128)/ReLU/dropout/multiclass logits. Training uses balanced replacement sampling, fresh RGB augmentation, cross-entropy, AdamW, full validation data, and validation-loss early stopping. No class weights are combined with balanced sampling. Optional dropout trials [0.3,0.4,0.5,0.6,0.7] select on validation only; default is 0.35. Training and final testing have separate run switches. Full training has not been performed as part of assembly.

New run directories under `runs/four-model-transfer/` store exact split plans and, after training, head checkpoints with official-backbone reconstruction metadata, preprocessing, class mappings, history, and metrics. Final test evaluation checks saved test membership. Metrics are multiclass accuracy, macro precision/recall/F1, and top-1/3/5/10/20 accuracy; binary AUC/thresholding from the old notebook are not reused. Top-k measures the fraction of images whose true cultivar occurs among the first k predictions, with k capped at the output class count and tied scores ordered by class ID. Training runs log/save validation top-k metrics. Prediction defaults to a ranked top-20 table and accepts `actual_class` to mark the correct cultivar and report its full-list rank. Compare architectures within each benchmark rather than interpreting the four datasets as one leaderboard. Full-image labels/rulers/backgrounds remain visible; fruit cropping is still pending.

User requested the top-k workflow directly in the active notebook. The **Top-k cultivar accuracy** section now sits immediately after the training cell, with the calculation inline and a percentage table for validation top-1/3/5/10/20 per dataset/architecture. It reuses completed training results (or the latest completed saved checkpoint per configuration), computes missing metrics for older checkpoints using their saved validation rows, and marks unfinished configurations as awaiting training. This cell does not access the test split or start training. The final-test cell remains a separate optional evaluation; its former top-k-only table has moved to this visible validation section.

Verification: focused split/sampler/training tests passed, and all 12 real pretrained configurations passed forward/backward checks with unchanged frozen backbone buffers. Official weights are cached under `runs/.torch-cache/`. Notebook setup cells execute without launching the 12-run training sweep.

## Project intent

Build a mango-variety image classifier that can eventually work on guided phone photographs. The first model will likely use ImageNet transfer learning. The initial target is an intact, exterior mango photographed as one main subject; cut-open fruit and arbitrary uncontrolled photos are later experiments.

## Data locations

```text
data/raw/                  Original source files. Do not edit.
data/raw/sharepoint_data/  UF SharePoint / OneDrive mango images.
data/raw/hugging_face_data/ Hugging Face dataset files.
data/transformed/          Generated decoded, cropped, or otherwise cleaned images.
data/manifests/            CSV/JSON tables mapping samples to paths, labels, and metadata.
data/splits/               Group-aware train/validation/test sample lists.
notebooks/                 Exploratory audits and one-off investigations.
scripts/                   Reusable command-line data and training utilities.
```

The SharePoint source contains `.HEIC` images and same-stem `.MOV` companions. The MOV files appear to be Apple Live Photo companions and are cataloged as related media; they are not separate v1 training examples.

Raw files remain the source of truth. Generated outputs belong under `data/transformed/` and should be reproducible from the raw files plus committed manifests/configuration.

## uv workflow

The project uses uv for Python environments and dependencies. Commands should be run from `ml-models/`.

If the uv project has not been initialized yet:

```bash
uv init
```

Notebook dependencies:

```bash
uv add --dev jupyter pandas matplotlib pillow pillow-heif
```

Install the committed Python 3.12 environment:

```bash
uv sync --locked
```

Run project commands through the uv environment:

```bash
uv run <command>
```

Do not install project dependencies globally and do not commit virtual environments, API keys, rclone tokens, or local caches.

## Hugging Face download

From `ml-models/`, run:

```bash
uv sync --locked
uv run python scripts/download_hugging_face.py
uv run python scripts/download_hugging_face.py --split train
```

The script downloads `earl562/mango-varieties` to `data/raw/hugging_face_data/`. It pins commit `f482454c26bcab8137b0eed3e45317e8bf6ff260` so teammates get the same source version, even if upstream changes. All splits download by default; repeat `--split` to select multiple splits. `--output` overrides the destination; explicit relative paths resolve from the working directory.

The source is approximately 466 MB: 3,093 train, 458 validation, and 529 test examples. Images and `variety_name` labels remain in the original `data/*.parquet` files alongside source metadata; this is not an extracted JPEG directory. Keep extraction or cleaning under `data/transformed/`. These upstream splits are source data, not a guarantee of leakage-free project evaluation splits.

Rerun the same command after an interruption. Hugging Face handles cached downloads and partial-file recovery; keep the destination's `.cache/huggingface/` metadata. Split selection adds files without deleting previously downloaded splits. Raw downloads and their caches are already gitignored. The dataset is public; no token is required. An optional `HF_TOKEN` can be supplied in the shell or root `.env` (existing environment variables take precedence).

To intentionally update the dataset, change the pinned revision in the script and this context together, and use a fresh destination to avoid mixing old files with a new snapshot. Do not edit downloaded raw files.

## Gemini annotations

`scripts/annotate_mangoes.py` processes raw SharePoint HEICs through Gemini's Interactions API (`client.interactions.create`), three images per request by default, with requests sent sequentially. This is the regular API, not asynchronous Batch. Requests use a Pydantic JSON schema and `store=False`; progress is persisted locally. Run from `ml-models/`:

```bash
uv run python scripts/annotate_mangoes.py
uv run python scripts/annotate_mangoes.py --limit 20
uv run python scripts/annotate_mangoes.py --export-only
```

No flags means all unfinished images. The limit counts images, not groups. Use `--input` for a source directory, `--output` for a JSONL results file, `--model` to change the model, `--group-size` (1–5, default 3), or `--delay` to change the default two-second pause between requests. Rate-limit retries still use longer backoff. Explicit relative paths resolve from the working directory; default paths resolve from the script.

Each grouped response must have exactly one unique image ID per input. Responses are matched by ID, not order, and saved as individual records: one image per JSONL line, never nested groups. The final request may contain fewer than three images. Invalid groups are retried once and left unfinished if still invalid; three consecutive invalid groups stop the run. Already-saved results from the original single-image prompt are accepted during migration. New grouped results fingerprint the group prompt/schema and configured group size. An interruption during saving may repeat only the unsaved images, even if Google already processed them.

Set `GEMINI_API_KEY` in the repository-root `.env` or shell; existing environment variables take precedence. Results are saved immediately in `data/manifests/sharepoint_gemini/annotations.jsonl`. Rerun the same command after an interruption to reuse successful annotations matching the source path/hash, model, and prompt/schema fingerprint. Valid missing labels also count as completed responses. An in-flight request interrupted before saving may be repeated.

Each result preserves the full `post_it_text`, cultivar transcription, specimen code, exterior/interior/unknown view, and readability flag, plus source and request provenance. These are draft annotations, not human-approved labels. CSV export is offline and writes `annotations.csv` beside the results with pending review status. It includes the latest successful source revision per model/prompt configuration; it is not automatically a current training manifest.

Saved records contain only `raw_path`, `sha256`, `model`, `fingerprint`, `completed_at`, and `annotation`. Older records with extra fields still resume correctly. CSV exports omit the redundant sample ID.

Retries back off before stopping with progress preserved. Fatal API errors stop immediately. Sanitized errors appear only in the CLI, including the provider message, API code, and request ID when available; no error file is written. Full request/response bodies are not logged. An exclusive lock prevents concurrent writers to the same output. Unreadable-file and invalid-response failures remain eligible on the next run. Completed results are never deleted automatically.

The installed SDK exposes Interactions errors through `google.genai._gaos.lib.compat_errors` and needs an explicit Interactions retry override to avoid extra automatic retries. Recheck these SDK-specific details when upgrading `google-genai`; run `uv run pytest tests/test_annotate_mangoes.py` (mocked requests, no API quota).

Tests: `uv run pytest tests/test_annotate_mangoes.py` (mocked; no paid calls).

## Planned cleaning flow

```text
raw HEIC/MOV files
    -> inventory and file validation
    -> HEIC decode, orientation correction, RGB/sRGB conversion
    -> Gemini annotation suggestion (including full post-it transcription)
    -> human label and view-type review
    -> reviewed mango bounding box
    -> padded JPEG crop in data/transformed/
    -> approved training manifest
```

The cleaner should be staged and resumable. It must never overwrite raw files. A proposed box is only a suggestion; the reviewer approves or corrects the final crop. The crop should remove the handwritten label card and ruler while retaining the whole fruit and modest context.

## Manifest conventions

Manifests are the dataset tables of contents. They map each sample to its source and derived files and carry the decisions needed by training code.

Useful fields include:

```text
sample_id
raw_path
transformed_path
companion_mov
sha256
post_it_text
variety_raw
variety_canonical
specimen_code
view_type              # exterior, interior, unknown
bbox_xmin/ymin/xmax/ymax
status                 # pending, approved, rejected
review_notes
```

Keep the exact handwritten text separate from the normalized cultivar label. Do not silently infer a cultivar from an OCR result. Preserve the original specimen/accession code even when its meaning is not yet confirmed.

The intended manifest progression is:

```text
inventory.csv       Automatically discovered facts.
annotations.csv     Annotation suggestions plus human corrections and crop decisions.
training.csv        Derived approved samples eligible for a particular experiment.
```

## Modeling assumptions

- V1 training uses approved exterior-fruit crops.
- Interior/cut-fruit images remain cataloged and tagged for later experiments.
- Bounding boxes are preprocessing annotations; the first classifier receives image crops, not box coordinates.
- Keep high-resolution transformed crops. The model loader performs model-specific resizing and ImageNet normalization.
- Training augmentation can vary lighting, framing, and mild blur. Validation/test preprocessing must be deterministic.
- Related views of the same physical fruit, tree, or specimen must stay in one split.
- A realistic phone-photo test set is required; random splits of controlled lab photos are insufficient by themselves.

## Working rules

- Use relative paths from `ml-models/` in committed manifests.
- Use stable sample IDs based on the source filename unless a later source-specific ID is established.
- Flag duplicates for review rather than deleting them automatically.
- Keep preprocessing settings and source hashes with generated manifests so outputs can be invalidated and rebuilt when settings change.
- Move reusable notebook logic into scripts or shared modules once the exploratory behavior is settled.

## Imported notebook audit (2026-10-04)

Read-only audit of `notebooks/CNN.ipynb` and `notebooks/data_preprocessing.ipynb`, including saved outputs; no old training or downloads were rerun. These are binary chest-X-ray experiments, not mango experiments. Recommendations below are proposals for early model development, not an approved training configuration.

- `CNN.ipynb`: grayscale 224x224 images, /255 scaling, random stratified 70/15/15 image splits, three convolution/pooling blocks, Flatten + Dense(128) + Dropout(0.5), binary sigmoid output, 10 epochs. Trained from scratch; the Flatten head alone has roughly 11 million parameters. Saved test accuracy is 96.12%; this is not evidence for mango performance.
- `data_preprocessing.ipynb`: path/label DataFrame and dimension/class EDA; RGB 224x224 pipeline with /255 scaling; training-only flips, brightness/contrast, and random 0/90/180/270-degree rotations; batched/prefetched tf.data datasets; training-only class weights. Frozen ImageNet VGG16/ResNet50/EfficientNetB0 + global average pooling + dropout + Dense(128)/BatchNorm + sigmoid, trained for 10 epochs. No backbone fine-tuning is implemented. Also compares SVM/logistic regression/random forest on the trained ResNet head's features (not raw frozen-backbone embeddings).
- Correctness issues: directory class meanings conflict between notebooks; source semantics need verification. A sample filename includes `bacteria`, so a COVID-specific interpretation is not established by the notebook. EfficientNet incorrectly receives [-1,1]; Keras EfficientNetB0 expects [0,255] with internal rescaling (https://keras.io/api/applications/efficientnet/efficientnet_models/). Its poor saved result is not a fair architecture comparison.
- Evaluation issues: dropout sweep evaluates test subsets during tuning; `.take()` selects batches and shuffled training subsets can change between trials. For validation/test cardinality 15 and fraction 0.1, this selects only one 32-image batch. Metric-name zipping produces incomplete `compile_metrics` reports; use evaluate(return_dict=True). Saved logs say `auc_roc` while current compilation names `auc`, so outputs are not a fully reproducible record of current source. CNN ROC AUC uses thresholded labels instead of continuous scores. Split proportions are preserved, not balanced. Neither notebook establishes patient/specimen grouping or duplicate-safe splitting.
- Mango proposals: preserve RGB/color and fruit shape; decode HEIC and apply EXIF orientation; approve padded fruit-only crops removing label cards/rulers; aspect-preserving resizing; mild training-only augmentation; frozen pretrained backbone with a small multiclass head or logistic regression on pooled backbone embeddings. Use one stable reviewed class mapping and group-aware splits across models. Evaluate macro F1/per-class recall/top-k plus accuracy; tune on validation only; select best validation checkpoint before final test. Class weights/augmentation cannot compensate for missing independent specimens.
- Dataset context from audit: 222 normalized classes, 194 after proposed spelling merges; 751 cultivar-labeled exterior records covering 192 proposed classes, 160 of which have <=5 exterior images. HF has 64 candidate shared classes; matched names cover 2,002 HF records and 287 SharePoint exterior records, but suitability/labels are unapproved. Start with supported reviewed classes rather than claiming full-catalog performance.
- User preference: concise notebook outputs; no redundant CSV review reports. Preserve the necessary `data/manifests/sharepoint_gemini/annotations_mapping.csv` derived directly from JSONL.

## Initial baseline implementation (2026-10-04)

`notebooks/inital_model_development.ipynb` now implements and has executed a SharePoint-only PyTorch baseline. It uses provisional spelling aliases, exterior-only labeled records with known specimen codes, global code grouping joined transitively with exact-hash groups, and deterministic class-complete group splits. Ten selected classes have 122 images: 72 training, 25 validation, 25 test. Group keys are conservative accession/location proxies, not verified physical-fruit IDs.

HEIC decoding, EXIF orientation, RGB conversion, optional manually reviewed crop boxes, square padding and 224x224 ImageNet-normalized inputs feed a frozen ResNet-18. Deterministic 512-dimensional features are extracted once (no augmentation in this initial experiment). Compare normalized nearest-centroid classification against a dropout/linear head trained with AdamW and validation-loss early stopping. Report accuracy, macro F1, top-3 accuracy, support, and confusion matrix. No TensorFlow/scikit-learn dependency was added.

Full notebook execution and checkpoint/split/metric checks passed. Exploratory whole-image held-out results: centroid 36% accuracy, macro F1 0.209; linear head 32%, macro F1 0.143; both 68% top-3 accuracy. These are 25-image test results with unapproved labels/crops and potential label-card/background shortcuts, not validated mango-only or phone-photo performance. Do not tune further against these test scores. The best head checkpoint was epoch 2.

Artifacts are stored under `runs/initial-resnet18-20261004T184643176226Z/`: `model.pt` (backbone/head/centroids/class names) and `experiment.json` (configuration, class crosswalk, exact splits/source hashes/history/metrics). Official pretrained weights are cached under `runs/.torch-cache/`. `REQUIRE_REVIEWED_CROPS=True` filters to manually reviewed crop entries; none are currently supplied. The initial ten-class baseline excludes HF; the later all-222 continuation below implements a separate HF fine-tuning experiment.

## Full 222-class exploratory notebook

`notebooks/full_222_class_baseline.ipynb` is a separate experiment preserving all 222 case/whitespace-normalized labels (no spelling merges). It uses all labeled views to retain the full catalog: 751 exterior, 635 interior, 1 unknown before removing one duplicate, giving 1,386 records. This differs from exterior-only V1 and must not be compared as the same benchmark.

All classes are represented in training. Conservative global code/hash-connected groups remain together; missing-code groups are forced into training. Fixed seed splits have 993 training images across 222 classes, 113 validation images across 33 classes, and 280 test images across 82 classes. There are 140 training-only classes. These remain in the 222-output model but cannot be assessed for held-out generalization. Supported-class macro F1 and all-222 zero-filled macro F1 are reported separately, with explicit coverage limits. Full-image label-card and background shortcuts remain possible.

Full-222 notebook execution completed and outputs saved. On 280 test images covering 82 true classes, centroid accuracy was 3.93% (top-3 8.57%) and the linear head 1.43% (top-3 3.21%); the validation-loss-selected head was epoch 1. These low mixed-view exploratory results do not establish performance on the 140 untested classes. Checkpoint and split coverage checks passed, including a (222,512) classifier weight matrix and 222 training classes. Artifacts: `runs/full-222-resnet18-20261004T190744711354Z/`. Avoid further tuning on this test set.


## HF continuation of all-222 baseline (2026-10-04)

Sections 12–18 of `notebooks/full_222_class_baseline.ipynb` now run independently from an explicit saved baseline (`runs/full-222-resnet18-20261004T190744711354Z/`). They preserve its 222 class IDs and exact SharePoint splits. Only the local HF train split is used. Case/whitespace and explicit retail suffix cleanup yield 1,586 matched training records across 56 classes; no fuzzy mapping, spelling merges, or upstream validation/test additions. All 1,586 passed decode, standardized pixel-hash, and conservative 64-bit dHash screening (distance <=2 against all SharePoint inputs). This screening does not prove absence of all related/recompressed images. There are 2,579 training images, with the original 113 validation and 280 test images.

The saved visual preview includes saplings/foliage and food-preparation images. HF rows are label-matched candidates, not reviewed fruit-only examples. This is an explicit unreviewed external-data experiment; additional curation is necessary for a fruit-only model.

Actual fine-tuning updates layer4 convolution weights and the classifier; all earlier layers and BatchNorm affine parameters/statistics stay frozen. Layer3 spatial maps are cached with source/preprocessing/checkpoint fingerprints under `runs/.hf-finetune-cache/`. Inputs are deterministic without augmentation. Each source contributes equal total loss per epoch. AdamW rates: layer4 1e-5, head 3e-4; weight decay 0.01, gradient clipping 1.0, batch 16, up to five epochs, patience two. Training stopped after epoch 3 and restored epoch 1 by SharePoint validation loss (6.195 -> 5.150).

On the SAME previously inspected test set (280 images, 82 supported true classes), the frozen linear-head baseline had 1.43% accuracy and 3.21% top-3; HF+layer4 fine-tuning achieved 2.14% accuracy (6 correct vs 4), 4.64% top-3, and supported-class macro F1 0.0169. This small descriptive change combines data and training-method changes; it does not establish a meaningful improvement or independent generalization. The prior centroid result (3.93% accuracy) remains higher. The other 140 classes remain unmeasured.

Artifacts: `runs/full-222-hf-finetune-20261004T192139020172Z/model.pt` and `experiment.json`, including exact HF Parquet row/source IDs, label matches, screening settings, original split membership, cache provenance, history, and before/after metrics. Full execution passed; saved checkpoints verified that layer4 changed, earlier layers/BatchNorm stayed identical, all 222 outputs remain, HF rows are train-only, and original SharePoint holdouts are unchanged. No CSV reports were added; the necessary annotations mapping is preserved.
