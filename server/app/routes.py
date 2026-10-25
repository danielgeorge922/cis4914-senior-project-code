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

    images = [await upload.read() for upload in files]
    tensors = await run_in_threadpool(
        lambda: [to_tensor(state.cropper.crop(load_image(data)), settings) for data in images]
    )

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
    measurements = {name: float(value) for name, value in json.loads(features).items()}
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
