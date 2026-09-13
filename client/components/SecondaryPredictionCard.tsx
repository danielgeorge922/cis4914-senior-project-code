import type { Prediction } from "../lib/types";
import PredictionScore from "./PredictionScore";

export default function SecondaryPredictionCard({
  prediction,
}: {
  prediction: Prediction;
}) {
  return (
    <article className="min-w-0 rounded-2xl bg-gray-50 p-5 transition-colors hover:bg-gray-100 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-gray-500">
            Rank {String(prediction.rank).padStart(2, "0")}
          </p>
          <h3 className="mt-2 text-2xl font-semibold text-uf-blue">
            {prediction.name}
          </h3>
        </div>
        <PredictionScore score={prediction.matchScore} />
      </div>
      <details className="mt-5 border-t border-gray-200 pt-4">
        <summary className="cursor-pointer text-sm font-medium text-uf-blue">
          View identifying traits
        </summary>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-gray-600">
          {prediction.traits.map((trait) => (
            <li key={trait}>{trait}</li>
          ))}
        </ul>
      </details>
    </article>
  );
}
