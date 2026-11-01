"use client";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Photo } from "../lib/types";
import { startPrediction } from "../lib/api";
import { useRouter } from "next/navigation";
import ImageUploadCard from "./ImageUploadCard";
import ExtraFeatures, { type Row } from "./ExtraFeatures";
import ExampleModal from "./ExampleModal";
import { useLanguage } from "../lib/i18n";

export default function MangoUploadForm() {
  const router = useRouter();
  const { t } = useLanguage();
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [features, setFeatures] = useState<Row[]>([]);
  const [selectedModel, setSelectedModel] = useState("classifier");
  const [modalView, setModalView] = useState<"exterior" | "interior" | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(0);
  const urls = useRef(new Set<string>());

  const categories = [
    {
      kind: "exterior" as const,
      title: t("fruitTitle"),
      description: t("fruitDesc"),
      tip: t("fruitTip"),
    },
    {
      kind: "interior" as const,
      title: t("interiorTitle"),
      description: t("interiorDesc"),
      tip: t("interiorTip"),
    },
  ];

  useEffect(() => {
    const active = urls.current;
    return () => active.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  async function addPhotos(files: File[], kind: Photo["kind"]) {
    setPending((count) => count + 1);
    const accepted: Photo[] = [];
    const errors: string[] = [];
    for (const file of files) {
      if (
        !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
        file.size > 10 * 1024 * 1024
      ) {
        errors.push(
          `${file.name}: use a JPG, PNG, or WebP no larger than 10 MB.`,
        );
        continue;
      }
      const url = URL.createObjectURL(file);
      try {
        const image = new window.Image();
        image.src = url;
        await image.decode();
        urls.current.add(url);
        accepted.push({
          id: crypto.randomUUID(),
          url,
          name: file.name,
          kind,
          file,
        });
      } catch {
        URL.revokeObjectURL(url);
        errors.push(`${file.name} could not be opened. Try another image.`);
      }
    }
    setPhotos((previous) => [...previous, ...accepted]);
    setError(errors.join(" "));
    setPending((count) => count - 1);
  }

  function removePhoto(photo: Photo) {
    URL.revokeObjectURL(photo.url);
    urls.current.delete(photo.url);
    setPhotos((previous) => previous.filter((item) => item.id !== photo.id));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!photos.length || pending) return;
    startPrediction(photos, features, selectedModel);
    router.push("/processing");
  }

  return (
    <>
      <form className="mt-9 sm:mt-12" onSubmit={handleSubmit}>
        <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-xl font-semibold">{t("uploadHeading")}</h2>
          <p className="text-sm text-gray-600">
            {t("uploadRequirement")}
          </p>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          {categories.map((category) => (
            <ImageUploadCard
              key={category.kind}
              category={category}
              photos={photos.filter((photo) => photo.kind === category.kind)}
              onAdd={addPhotos}
              onRemove={removePhoto}
              onSeeExample={() => setModalView(category.kind)}
            />
          ))}
        </div>

        <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-5 sm:p-6">
          <label
            htmlFor="model-select"
            className="block text-base font-semibold text-uf-blue"
          >
            {t("modelSelectLabel")}
          </label>
          <p className="mt-1 text-sm text-gray-600">
            {t("modelSelectDesc")}
          </p>
          <select
            id="model-select"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="mt-3 block w-full rounded-xl border border-gray-300 bg-gray-50 px-4 py-3 text-sm font-medium text-gray-900 focus:border-uf-blue focus:bg-white focus:outline-none focus:ring-2 focus:ring-uf-blue"
          >
            <option value="classifier">
              {t("modelClassifier")}
            </option>
            <option value="resnet50">
              {t("modelResnet50")}
            </option>
          </select>
        </div>

        <ExtraFeatures rows={features} setRows={setFeatures} />
        {error && (
          <p
            role="alert"
            className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"
          >
            {error}
          </p>
        )}

        <div className="mt-6 rounded-xl border border-blue-100 bg-blue-50/60 p-4 text-xs text-gray-700">
          <div className="flex items-center gap-2 font-semibold text-uf-blue">
            <svg
              className="h-4 w-4 shrink-0 text-uf-blue"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
              />
            </svg>
            <span>{t("privacyTitle")}</span>
          </div>
          <p className="mt-1.5 leading-relaxed text-gray-600">
            {t("privacyBody")}
          </p>
        </div>

        <div className="mt-7 flex flex-col gap-5 border-t border-gray-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p aria-live="polite" className="text-sm font-medium">
              {pending
                ? t("checkingImages")
                : photos.length
                  ? `${photos.length} ${t("imagesSelected")}`
                  : t("addImagesToStart")}
            </p>
            <p className="mt-1 text-xs leading-5 text-gray-500">
              {t("privacyBadge")}
            </p>
          </div>
          <button
            type="submit"
            disabled={!photos.length || pending > 0}
            className="cursor-pointer min-h-12 rounded-lg bg-uf-blue px-7 py-3 font-semibold text-white transition-colors hover:bg-uf-blue/90 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-uf-blue disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-500"
          >
            {t("identifyButton")}{" "}
            <span aria-hidden="true" className="ml-3">
              →
            </span>
          </button>
        </div>
      </form>

      <ExampleModal
        isOpen={modalView !== null}
        onClose={() => setModalView(null)}
        viewType={modalView ?? "exterior"}
      />
    </>
  );
}
