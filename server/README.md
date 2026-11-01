# Mango identification API

FastAPI server that takes photos of one tree, runs each through the fruit or leaf model on Triton, averages the scores, and returns a ranked list of cultivars. It is stateless: to refine a result, the app re-sends every photo.

## Setup and Run

Install dependencies and create the virtual environment using [uv](https://docs.astral.sh/uv/):

```bash
cd server
uv sync
```

### Run Locally

**Without Triton / Mock Mode** (instant local development with deterministic scores):

- On macOS / Linux:
  ```bash
  MOCK_INFERENCE="true" uv run uvicorn app.main:app --port 8080
  ```
- On Windows (PowerShell):
  ```powershell
  $env:MOCK_INFERENCE="true"; uv run uvicorn app.main:app --port 8080
  ```

**With Local ONNX Runtime** (uses models in `model_repository/` directly):
```bash
uv run uvicorn app.main:app --port 8080
```

**With Triton via Docker**:
```bash
docker compose up --build
```

## API

`POST /api/v1/predict`, multipart. Send one `files` and one `kinds` (`fruit` or `leaf`) per photo, in the same order. The server doesn't validate uploads; the frontend checks them.

```sh
curl -F files=@leaf.jpg -F kinds=leaf localhost:8080/api/v1/predict
```

It returns `{ demo, predictions }`. `demo` is true in mock mode. `predictions` is the top 10 in the shape of `Prediction` in `client/lib/types.ts`. `matchScore` is the cultivar's probability averaged over all photos, from 0 to 100.

Optional `features` field: JSON measurements from the form, in cm, g and years, e.g. `{"Fruit weight": 450, "Leaf length": 22}`. A cultivar's score is multiplied by `RANGE_PENALTY` (0.5) for each measurement outside its range in `data/cultivars.json`, then all scores are rescaled to add up to 100. Cultivars without a range for that feature are unaffected. Ranges look like:

```json
"Kent": { "ranges": { "Fruit weight": [500, 900], "Leaf length": [15, 30] } }
```

No ranges are filled in yet; they need verified values from the advisors.

## Model export contract

Put each model in `model_repository/<fruit_classifier|leaf_classifier>/`:

- `config.pbtxt`: Triton model config, with backend `onnxruntime`.
- `1/model.onnx`: input `input` (FP32, `[batch, 3, 224, 224]`, normalized RGB), output `logits` (FP32, `[batch, classes]`).
- `labels.json`: cultivar names in output order. It must be identical for both models.
- Preprocessing must match training's evaluation transform. The server resizes the short side to 256, center-crops to 224, and applies the ImageNet mean and standard deviation. Change these in `app/config.py` if training differs.
