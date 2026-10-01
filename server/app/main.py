from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.routes import router
from app.services.catalog import Catalog, load_labels
from app.services.inference import MockClassifier, TritonClassifier

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    catalog = Catalog.load(settings.catalog_path)
    labels = load_labels(settings, catalog)
    app.state.settings = settings
    app.state.catalog = catalog
    app.state.labels = labels
    app.state.classifier = (
        MockClassifier(len(labels)) if settings.mock_inference else TritonClassifier(settings)
    )
    yield
    await app.state.classifier.aclose()


app = FastAPI(title="Mango cultivar identification API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
