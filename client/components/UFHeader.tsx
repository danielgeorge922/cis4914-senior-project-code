"use client";

import Link from "next/link";
import LanguageToggle from "./LanguageToggle";
import { useLanguage } from "../lib/i18n";

export default function UFHeader() {
  const { t } = useLanguage();

  return (
    <header className="shrink-0 border-b-4 border-uf-orange bg-uf-blue text-uf-white">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:p-3 focus:text-uf-blue"
      >
        {t("skipToMain")}
      </a>
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 sm:py-5 md:flex-row md:items-center md:justify-between lg:px-8">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center md:gap-6">
          <a
            href="https://www.ufl.edu/"
            className="flex min-h-11 w-fit max-w-full items-center text-base font-semibold tracking-wide underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 sm:text-lg"
          >
            {t("university")}
          </a>
          <Link
            href="/"
            className="block min-h-11 min-w-0 border-t border-white/30 pt-3 focus-visible:outline-2 focus-visible:outline-offset-4 sm:border-t-0 sm:border-l sm:pt-0 sm:pl-6"
          >
            <span className="block text-lg font-semibold break-words sm:text-xl">
              {t("appTitle")}
            </span>
            <span className="mt-0.5 block text-xs text-white/80 sm:text-sm">
              {t("byProfessor")}
            </span>
          </Link>
        </div>

        <div className="flex items-center justify-end">
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}
