"use client";
import Link from "next/link";
import { useState } from "react";
import PrimaryPredictionCard from "../../components/PrimaryPredictionCard";
import SecondaryPredictionCard from "../../components/SecondaryPredictionCard";
import SubmittedImageModal from "../../components/SubmittedImageModal";
import { clearPrediction, getLatestPrediction, getSubmittedPhotos } from "../../lib/api";
import { useLanguage } from "../../lib/i18n";
import type { PredictResponse, SubmittedPhoto } from "../../lib/types";

export default function PredictionsResultPage() {
  const { t } = useLanguage();
  const [result] = useState<PredictResponse | null>(() => getLatestPrediction());
  const [photos] = useState<SubmittedPhoto[]>(() => getSubmittedPhotos());
  const [showImageModal, setShowImageModal] = useState(false);

  if (!result) {
    return (
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto w-full max-w-2xl px-5 py-14 text-center"
      >
        <h1 className="text-3xl font-semibold tracking-tight">
          {t("noResultsTitle")}
        </h1>
        <p className="mt-3 text-gray-600">
          {t("noResultsDesc")}
        </p>
        <Link
          href="/"
          className="mt-7 inline-flex min-h-12 items-center rounded-lg bg-uf-blue px-6 font-semibold text-white hover:bg-uf-blue/90"
        >
          {t("goToUpload")}
        </Link>
      </main>
    );
  }

  const [primary, ...alternatives] = result.predictions;
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 lg:px-8"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold tracking-widest text-uf-blue uppercase">
            {t("resultsBadge")}
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("resultsTitle")}
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {photos.length > 0 && (
            <button
              type="button"
              onClick={() => setShowImageModal(true)}
              className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-gray-700 shadow-xs hover:border-uf-blue hover:bg-gray-50 hover:text-uf-blue transition-colors"
              title="Click to view your submitted photo"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photos[0].dataUrl}
                alt="Submitted photo preview"
                className="h-5 w-5 rounded-full object-cover border border-gray-200"
              />
              <span>{t("submittedPhoto")} 👁️</span>
            </button>
          )}

          {result.modelName && (
            <span className="inline-flex items-center rounded-full bg-blue-50 px-3.5 py-1.5 text-xs font-semibold text-uf-blue border border-blue-200">
              Model: {result.modelName}
            </span>
          )}
        </div>
      </div>

      <p className="mb-6 mt-3 text-gray-600">
        {t("topRankedDesc")}
      </p>
      {result.demo && (
        <p className="mb-6 rounded-lg bg-blue-50 p-4 text-sm leading-relaxed text-uf-blue">
          <strong>{t("demoResultsTitle")}</strong> {t("demoResultsBody")}
        </p>
      )}

      <div className="mb-4">
        <Link
          href="/"
          onClick={() => clearPrediction()}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3.5 py-1.5 text-sm font-semibold text-gray-700 shadow-xs hover:border-uf-blue hover:bg-gray-50 hover:text-uf-blue transition-colors"
        >
          <span aria-hidden="true" className="text-base leading-none">←</span>
          <span>{t("backToSubmission")}</span>
        </Link>
      </div>

      <PrimaryPredictionCard prediction={primary} />
      <h2 className="mb-5 mt-10 text-2xl font-semibold">
        {t("otherMatches")}
      </h2>
      <div className="grid gap-5 md:grid-cols-2">
        {alternatives.map((prediction) => (
          <SecondaryPredictionCard
            key={prediction.id}
            prediction={prediction}
          />
        ))}
      </div>
      <div className="mt-8 text-center">
        <Link
          href="/"
          onClick={() => clearPrediction()}
          className="inline-flex min-h-12 items-center rounded-lg bg-uf-blue px-6 font-semibold text-white hover:bg-uf-blue/90"
        >
          {t("identifyAnother")} →
        </Link>
      </div>

      <SubmittedImageModal
        isOpen={showImageModal}
        onClose={() => setShowImageModal(false)}
        photos={photos}
      />
    </main>
  );
}

