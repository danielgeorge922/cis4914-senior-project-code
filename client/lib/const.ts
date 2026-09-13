import type { Prediction } from "./types";

export const MOCK_PROCESSING_MS = 5000;

// Illustrative UI fixtures, not model output or verified botanical guidance.
export const MOCK_PREDICTION_RESPONSE: {
  demo: true;
  modelVersion: string;
  predictions: Prediction[];
} = {
  demo: true,
  modelVersion: "demo-v1",
  predictions: [
    "Kent",
    "Keitt",
    "Tommy Atkins",
    "Ataulfo",
    "Alphonso",
    "Haden",
    "Palmer",
    "Francis",
    "Kesar",
    "Valencia Pride",
  ].map((name, index) => ({
    id: name.toLowerCase().replaceAll(" ", "-"),
    rank: index + 1,
    name,
    matchScore: [82, 71, 64, 53, 46, 38, 31, 24, 18, 12][index],
    image: "/mango-placeholder.svg",
    imageAlt:
      "Placeholder mango illustration, not a cultivar reference photograph",
    description:
      index === 0
        ? "The closest match in this sample response. A real result will describe the cultivar and the characteristics that support its identification."
        : "A possible alternative in this sample ranking.",
    metadata: [
      { label: "Fruit shape", value: "Lorem ipsum" },
      { label: "Leaf profile", value: "Dolor sit amet" },
      { label: "Growing region", value: "Placeholder region" },
    ],
    traits: [
      "Fruit shape and proportions: placeholder identifying characteristic.",
      "Skin color and texture: placeholder identifying characteristic.",
      "Leaf shape and veins: placeholder identifying characteristic.",
    ],
  })),
};
