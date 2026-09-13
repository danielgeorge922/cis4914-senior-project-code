import Link from "next/link";
import PrimaryPredictionCard from "../../components/PrimaryPredictionCard";
import SecondaryPredictionCard from "../../components/SecondaryPredictionCard";
import { MOCK_PREDICTION_RESPONSE } from "../../lib/const";

export default function PredictionsResultPage() {
  const [primary, ...alternatives] = MOCK_PREDICTION_RESPONSE.predictions;
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
      <p className="mt-3 text-gray-600">
        Your top 10 cultivars, ranked by match score.
      </p>
      <p className="my-6 rounded-lg bg-blue-50 p-4 text-sm leading-relaxed text-uf-blue">
        <strong>Demo results.</strong> These scores, descriptions, and images
        are placeholders, not model predictions or verified cultivar guidance.
        No uploaded images have been analyzed.
      </p>
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
