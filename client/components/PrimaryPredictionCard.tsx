import Image from "next/image";
import type { Prediction } from "../lib/types";
import PredictionScore from "./PredictionScore";

export default function PrimaryPredictionCard({
  prediction,
}: {
  prediction: Prediction;
}) {
  return (
    <article className="rounded-3xl bg-gray-50 p-6 transition-colors hover:bg-gray-100 sm:p-8">
      <p className="mb-6 text-sm font-semibold tracking-widest text-uf-blue uppercase">
        Most Likely
      </p>
      <div className="flex flex-col items-start gap-7 lg:flex-row lg:items-center">
        <Image
          src={prediction.image}
          alt={prediction.imageAlt}
          width={240}
          height={240}
          priority
          className="aspect-square w-40 rounded-2xl bg-white object-contain sm:w-52"
        />
        <div className="min-w-0 flex-1">
          <h2 className="text-4xl font-semibold tracking-tight text-uf-blue sm:text-5xl">
            {prediction.name}
          </h2>
          <p className="mt-4 max-w-xl text-base leading-relaxed text-gray-600">
            {prediction.description}
          </p>
          <dl className="mt-6 grid gap-4 sm:grid-cols-3">
            {prediction.metadata.map((item) => (
              <div key={item.label}>
                <dt className="text-xs text-gray-500">{item.label}</dt>
                <dd className="mt-1 text-sm font-medium">{item.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <PredictionScore score={prediction.matchScore} large />
      </div>
      <details className="mt-7 border-t border-gray-200 pt-4">
        <summary className="cursor-pointer font-medium text-uf-blue">
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
