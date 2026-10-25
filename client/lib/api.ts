import type { Row } from "../components/ExtraFeatures";
import type { Photo, PredictResponse, SubmittedPhoto } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";
const STORAGE_KEY = "mango_active_prediction";
const PHOTOS_STORAGE_KEY = "mango_submitted_photos";

// In-memory prediction promises and cache
let request: Promise<PredictResponse> | null = null;
let latest: PredictResponse | null = null;
let submittedPhotos: SubmittedPhoto[] = [];

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new window.Image();
      img.onload = () => {
        const maxDim = 1200;
        let { width, height } = img;
        if (width > maxDim || height > maxDim) {
          if (width > height) {
            height = Math.round((height * maxDim) / width);
            width = maxDim;
          } else {
            width = Math.round((width * maxDim) / height);
            height = maxDim;
          }
        }
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        ctx?.drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.onerror = () => resolve(e.target?.result as string);
      img.src = e.target?.result as string;
    };
    reader.onerror = () => resolve("");
    reader.readAsDataURL(file);
  });
}

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

  // Cache submitted photos for display on inference results page
  void Promise.all(
    photos.map(async (p) => ({
      name: p.name,
      kind: p.kind,
      dataUrl: await fileToDataUrl(p.file),
    })),
  ).then((saved) => {
    submittedPhotos = saved;
    if (typeof window !== "undefined") {
      try {
        sessionStorage.setItem(PHOTOS_STORAGE_KEY, JSON.stringify(saved));
      } catch {
        // Ignore quota
      }
    }
  });

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

export function getSubmittedPhotos(): SubmittedPhoto[] {
  if (submittedPhotos.length > 0) return submittedPhotos;
  if (typeof window !== "undefined") {
    try {
      const cached = sessionStorage.getItem(PHOTOS_STORAGE_KEY);
      if (cached) {
        submittedPhotos = JSON.parse(cached) as SubmittedPhoto[];
      }
    } catch {
      sessionStorage.removeItem(PHOTOS_STORAGE_KEY);
    }
  }
  return submittedPhotos;
}

export function clearPrediction() {
  request = null;
  latest = null;
  submittedPhotos = [];
  if (typeof window !== "undefined") {
    try {
      sessionStorage.removeItem(STORAGE_KEY);
      sessionStorage.removeItem(PHOTOS_STORAGE_KEY);
    } catch {
      // Ignore
    }
  }
}
