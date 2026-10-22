"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getPendingPrediction } from "../../lib/api";
import { MOCK_PROCESSING_MS } from "../../lib/const";
import styles from "./processing.module.css";

export default function ProcessingPage() {
  const router = useRouter();
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  useEffect(() => {
    const request = getPendingPrediction();
    if (!request) {
      router.replace("/");
      return;
    }
    router.prefetch("/predictions-result");
    const started = performance.now();
    // Estimated progress; holds at 95% until the response arrives.
    const interval = window.setInterval(
      () =>
        setProgress(
          Math.min(
            95,
            Math.round(
              ((performance.now() - started) / MOCK_PROCESSING_MS) * 100,
            ),
          ),
        ),
      100,
    );
    let active = true;
    request
      .then(() => active && router.replace("/predictions-result"))
      .catch((reason: Error) => active && setError(reason.message))
      .finally(() => window.clearInterval(interval));
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [router]);
  if (error) {
    return (
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto flex w-full max-w-2xl flex-col items-center px-5 py-14 text-center sm:py-20"
      >
        <h1 className="text-3xl font-semibold tracking-tight text-uf-blue">
          We couldn&apos;t identify your mango
        </h1>
        <p role="alert" className="mt-4 max-w-md text-gray-600">
          {error}
        </p>
        <Link
          href="/"
          className="mt-7 inline-flex min-h-12 items-center rounded-lg bg-uf-blue px-6 font-semibold text-white hover:bg-uf-blue/90"
        >
          Back to upload
        </Link>
      </main>
    );
  }
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="mx-auto flex w-full max-w-2xl flex-col items-center px-5 py-14 text-center sm:py-20"
    >
      <span className="rounded-full bg-blue-50 px-4 py-2 text-xs font-semibold text-uf-blue">
        Preparing your results
      </span>
      <svg
        viewBox="0 0 180 180"
        className={styles.mango}
        fill="none"
        role="img"
        aria-label="A cheerful mango running"
      >
        <g stroke="#0021a5" strokeWidth="6" strokeLinecap="round">
          <path className={styles.legOne} d="M76 123l-15 27-20 1" />
          <path className={styles.legTwo} d="M101 122l15 22 18-10" />
        </g>
        <g className={styles.body}>
          <path
            d="M94 39C50 19 25 56 40 99c13 37 48 47 75 18 37-40 29-80-21-78Z"
            fill="#f2a900"
          />
          <path
            d="M94 39c0-15 9-24 19-28"
            stroke="#25613e"
            strokeWidth="5"
            strokeLinecap="round"
          />
          <path d="M97 27C74 30 65 16 66 8c19-3 32 5 31 19Z" fill="#438159" />
          <path
            d="M105 74v4m17-6v4m-16 14q8 9 17-2M47 88 28 103 15 94"
            stroke="#0021a5"
            strokeWidth="4"
            strokeLinecap="round"
          />
        </g>
        <path d="M28 162h115" stroke="#e5e7eb" strokeWidth="3" />
      </svg>
      <h1 className="text-3xl font-semibold tracking-tight text-uf-blue sm:text-4xl">
        Hollup, we working on
        <br />
        them results, twin.
      </h1>
      <p className="mt-4 max-w-md leading-relaxed text-gray-600">
        Our little mango is on the move. Your possible matches are coming right
        up.
      </p>
      <div className="mt-8 w-full max-w-sm">
        <div className="mb-2 flex justify-between text-sm text-gray-600">
          <span>Progress</span>
          <span>{progress}%</span>
        </div>
        <div
          role="progressbar"
          aria-label="Processing progress"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
          className="h-3 overflow-hidden rounded-full bg-gray-200"
        >
          <div
            className="h-full rounded-full bg-uf-blue transition-[width] motion-reduce:transition-none"
            style={{ width: progress + "%" }}
          />
        </div>
      </div>
      <Link
        href="/"
        className="mt-7 inline-flex min-h-11 items-center text-sm text-uf-blue underline underline-offset-4"
      >
        Cancel and return to upload
      </Link>
    </main>
  );
}
