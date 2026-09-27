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

Optional OCR assistance:

```bash
uv add --dev pytesseract
brew install tesseract
```

Run project commands through the uv environment:

```bash
uv run <command>
```

Do not install project dependencies globally and do not commit virtual environments, API keys, rclone tokens, or local caches.

## Planned cleaning flow

```text
raw HEIC/MOV files
    -> inventory and file validation
    -> HEIC decode, orientation correction, RGB/sRGB conversion
    -> optional OCR suggestion
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
ocr_text
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
annotations.csv     OCR suggestions plus human corrections and crop decisions.
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
