import type { Row } from "../components/ExtraFeatures";
import type { Photo, PredictResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
const STORAGE_KEY = "mango_active_prediction";

// In-memory prediction promises and cache
let request: Promise<PredictResponse> | null = null;
let latest: PredictResponse | null = null;

export function startPrediction(
  photos: Photo[],
  features: Row[],
  model: string = "classifier",
) {
  const body = new FormData();
  for (const photo of photos) {
    body.append("files", photo.file, photo.name);
    body.append("kinds", photo.kind);
  }
  body.append("model", model);

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
      latest = (await response.json()) as PredictResponse;
      if (typeof window !== "undefined") {
        try {
          sessionStorage.setItem(STORAGE_KEY, JSON.stringify(latest));
        } catch {
          // Ignore storage quota or disabled issues
        }
      }
      return latest;
    },
  );
}

export const getPendingPrediction = () => request;

export function getLatestPrediction(): PredictResponse | null {
  if (latest) return latest;
  if (typeof window !== "undefined") {
    try {
      const cached = sessionStorage.getItem(STORAGE_KEY);
      if (cached) {
        latest = JSON.parse(cached) as PredictResponse;
      }
    } catch {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  }
  return latest;
}

export function clearPrediction() {
  request = null;
  latest = null;
  if (typeof window !== "undefined") {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore
    }
  }
}
