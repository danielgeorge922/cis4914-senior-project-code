export default function PredictionScore({
  score,
  large = false,
}: {
  score: number;
  large?: boolean;
}) {
  return (
    <div className="shrink-0 text-center">
      <div
        role="img"
        aria-label={score + "% demo match score"}
        className={`relative ${large ? "h-36 w-36 sm:h-44 sm:w-44" : "h-20 w-20"}`}
      >
        <svg
          viewBox="0 0 100 100"
          className="h-full w-full -rotate-90"
          fill="none"
          strokeWidth="8"
          aria-hidden="true"
        >
          <circle cx="50" cy="50" r="42" className="stroke-gray-200" />
          <circle
            cx="50"
            cy="50"
            r="42"
            pathLength="100"
            strokeDasharray={score + " 100"}
            strokeLinecap="round"
            className="stroke-uf-blue"
          />
        </svg>
        <span
          className={`absolute inset-0 flex items-center justify-center font-semibold text-uf-blue ${large ? "text-4xl sm:text-5xl" : "text-xl"}`}
        >
          {score}
          <span className="text-[0.55em]">%</span>
        </span>
      </div>
      <p className="mt-2 text-xs text-gray-600">Match score</p>
    </div>
  );
}
