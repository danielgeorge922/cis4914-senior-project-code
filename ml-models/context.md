# ML Models Working Context

This file is the living handoff for the mango data and modeling work. Update it when the data contract, commands, or preprocessing decisions change.

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
