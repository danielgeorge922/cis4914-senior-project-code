import json
from collections import defaultdict

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.schemas import Kind, Prediction, PredictResponse
from app.services.aggregate import apply_ranges, combine, softmax, top_k
from app.services.inference import InferenceUnavailable, OnnxClassifier
from app.services.preprocess import load_image, to_tensor

router = APIRouter(prefix="/api/v1")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit per photo
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_MODELS = {"classifier", "resnet50", "retrieval"}
MAX_FILES = 10

MODEL_DISPLAY_NAMES = {
    "classifier": "EfficientNet-B0 (78 Classes)",
    "resnet50": "ResNet-50 (78 Classes)",
    "retrieval": "DINOv2 Retrieval",
}


@router.post("/predict", response_model=PredictResponse)
async def predict(
    request: Request,
    files: list[UploadFile] = File(..., description="Photos of one tree"),
    kinds: list[Kind] = Form(..., description="exterior or interior for each photo, in the same order"),
    features: str = Form("{}", description='Optional measurements as JSON, e.g. {"Fruit weight": 450}'),
    model: str = Form("classifier", description="Model architecture to use for prediction"),
) -> PredictResponse:
    state = request.app.state
    settings = state.settings

    # 1. Validate file counts and kinds alignment
    if not files:
        raise HTTPException(400, "At least one photo must be provided.")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Cannot upload more than {MAX_FILES} photos per submission.")
    if len(files) != len(kinds):
        raise HTTPException(400, "Number of photos must match number of kinds specified.")

    # 2. Validate model architecture selection
    if model not in ALLOWED_MODELS:
        raise HTTPException(
            400, f"Invalid model '{model}'. Allowed models: {', '.join(sorted(ALLOWED_MODELS))}."
        )

    # 3. Validate and parse features JSON
    try:
        raw_features = json.loads(features)
        if not isinstance(raw_features, dict):
            raise ValueError()
        measurements = {name: float(value) for name, value in raw_features.items()}
    except (json.JSONDecodeError, ValueError, TypeError):
        raise HTTPException(400, "Features must be a valid JSON object with numeric values.")

    # 4. Read and validate file sizes and MIME types
    images: list[bytes] = []
    for upload in files:
        if upload.content_type and upload.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                400,
                f"Unsupported file type '{upload.content_type}' for {upload.filename}. Allowed types: JPG, PNG, WebP.",
            )

        content = await upload.read(MAX_FILE_SIZE + 1)
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                400, f"File '{upload.filename}' exceeds maximum allowed size of 10 MB."
            )
        images.append(content)

    # 5. Decode images and generate normalized tensors
    def process_images() -> list[np.ndarray]:
        tensors = []
        for upload, data in zip(files, images):
            try:
                img = load_image(data)
            except Exception as error:
                raise HTTPException(
                    400, f"File '{upload.filename}' is corrupted or not a valid image."
                ) from error
            tensors.append(to_tensor(state.cropper.crop(img), settings))
        return tensors

    tensors = await run_in_threadpool(process_images)

    # Route each photo to the model for its kind (one call per model).
    batches: dict[Kind, list[np.ndarray]] = defaultdict(list)
    for kind, tensor in zip(kinds, tensors):
        batches[kind].append(tensor)

    try:
        if isinstance(state.classifier, OnnxClassifier):
            logits = [await state.classifier.infer(kind, np.stack(batch), model_name=model) for kind, batch in batches.items()]
        else:
            logits = [await state.classifier.infer(kind, np.stack(batch)) for kind, batch in batches.items()]
    except InferenceUnavailable as error:
        raise HTTPException(503, "The identification service is unavailable. Try again shortly.") from error

    scores = combine(softmax(np.concatenate(logits)))
    ranges = [state.catalog.ranges(label) for label in state.labels]
    scores = apply_ranges(scores, ranges, measurements, settings.range_penalty)
    predictions = [
        Prediction(
            **state.catalog.describe(state.labels[index]),
            rank=rank,
            match_score=round(score * 100, 1),
        )
        for rank, (index, score) in enumerate(top_k(scores, settings.top_k), start=1)
    ]
    display_name = MODEL_DISPLAY_NAMES.get(model, model.title())
    return PredictResponse(
        demo=settings.mock_inference,
        model_name=display_name,
        predictions=predictions,
    )
