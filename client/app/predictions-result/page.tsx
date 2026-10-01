"use client";
import Link from "next/link";
import PrimaryPredictionCard from "../../components/PrimaryPredictionCard";
import SecondaryPredictionCard from "../../components/SecondaryPredictionCard";
import { getLatestPrediction } from "../../lib/api";

export default function PredictionsResultPage() {
  const result = getLatestPrediction();
  if (!result) {
    return (
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto w-full max-w-2xl px-5 py-14 text-center"
      >
        <h1 className="text-3xl font-semibold tracking-tight">
          No results to show
        </h1>
        <p className="mt-3 text-gray-600">
          Upload photos of your mango tree to see its possible matches.
        </p>
        <Link
          href="/"
          className="mt-7 inline-flex min-h-12 items-center rounded-lg bg-uf-blue px-6 font-semibold text-white hover:bg-uf-blue/90"
        >
          Go to upload
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
      <p className="text-sm font-semibold tracking-widest text-uf-blue uppercase">
        Identification results
      </p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
        Meet your possible matches.
      </h1>
      <p className="mb-6 mt-3 text-gray-600">
        Your top 10 cultivars, ranked by match score.
      </p>
      {result.demo && (
        <p className="mb-6 rounded-lg bg-blue-50 p-4 text-sm leading-relaxed text-uf-blue">
          <strong>Demo results.</strong> The server is running without a
          trained model, so these scores are random placeholders, not
          predictions.
        </p>
      )}
      <PrimaryPredictionCard prediction={primary} />
      <h2 className="mb-5 mt-10 text-2xl font-semibold">
        Other possible matches
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
          className="inline-flex min-h-12 items-center rounded-lg bg-uf-blue px-6 font-semibold text-white hover:bg-uf-blue/90"
        >
          Identify another mango →
        </Link>
      </div>
    </main>
  );
}
