import type { Row } from "../components/ExtraFeatures";
import type { Photo, PredictResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

// Shared between pages during client-side navigation; lost on a full reload.
let request: Promise<PredictResponse> | null = null;
let latest: PredictResponse | null = null;

export function startPrediction(photos: Photo[], features: Row[]) {
  const body = new FormData();
  for (const photo of photos) {
    body.append("files", photo.file, photo.name);
    body.append("kinds", photo.kind);
  }
  // Only rows with a chosen feature and a numeric value, e.g. {"Fruit weight": 450}.
  const measurements = Object.fromEntries(
    features
      .filter((row) => row.feature && Number.isFinite(parseFloat(row.value)))
      .map((row) => [row.feature, parseFloat(row.value)]),
  );
  body.append("features", JSON.stringify(measurements));
  request = fetch(`${API_URL}/api/v1/predict`, { method: "POST", body }).then(
    async (response) => {
      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(
          typeof error?.detail === "string"
            ? error.detail
            : "Something went wrong. Try again.",
        );
      }
      latest = await response.json();
      return latest as PredictResponse;
    },
  );
}

export const getPendingPrediction = () => request;
export const getLatestPrediction = () => latest;
