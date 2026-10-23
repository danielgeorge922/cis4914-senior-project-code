from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Kind = Literal["fruit", "leaf"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class MetadataItem(CamelModel):
    label: str
    value: str


# Mirrors Prediction in client/lib/types.ts.
class Prediction(CamelModel):
    id: str
    rank: int
    name: str
    match_score: float
    image: str
    image_alt: str
    description: str
    metadata: list[MetadataItem]
    traits: list[str]


class PredictResponse(CamelModel):
    demo: bool
    predictions: list[Prediction]
