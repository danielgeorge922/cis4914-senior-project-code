"use client";

import MangoUploadForm from "../components/MangoUploadForm";
import { useLanguage } from "../lib/i18n";

export default function Home() {
  const { t } = useLanguage();

  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8"
    >
      <div className="max-w-3xl">
        <p className="mb-3 text-sm font-semibold tracking-widest text-uf-blue uppercase">
          {t("heroBadge")}
        </p>
        <h1 className="text-3xl leading-tight font-semibold tracking-tight text-uf-blue sm:text-4xl lg:text-5xl">
          {t("heroTitle")}
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-gray-700 sm:text-lg">
          {t("heroDesc")}
        </p>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-600">
          {t("heroNotice")}
        </p>
      </div>
      <MangoUploadForm />
    </main>
  );
}
