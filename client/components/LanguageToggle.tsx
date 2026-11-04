"use client";

import { useLanguage } from "../lib/i18n";

export default function LanguageToggle() {
  const { lang, setLang } = useLanguage();

  return (
    <div
      role="group"
      aria-label="Language selector"
      className="inline-flex items-center rounded-full border border-white/30 bg-black/20 p-0.5 text-xs font-semibold backdrop-blur-xs"
    >
      <button
        type="button"
        onClick={() => setLang("en")}
        aria-pressed={lang === "en"}
        className={`inline-flex cursor-pointer items-center gap-1 rounded-full px-2.5 py-1 transition-all ${
          lang === "en"
            ? "bg-white text-uf-blue shadow-xs"
            : "text-white/80 hover:text-white"
        }`}
      >
        <span>🇺🇸</span>
        <span>EN</span>
      </button>
      <button
        type="button"
        onClick={() => setLang("pt")}
        aria-pressed={lang === "pt"}
        className={`inline-flex cursor-pointer items-center gap-1 rounded-full px-2.5 py-1 transition-all ${
          lang === "pt"
            ? "bg-white text-uf-blue shadow-xs"
            : "text-white/80 hover:text-white"
        }`}
      >
        <span>🇧🇷</span>
        <span>PT</span>
      </button>
    </div>
  );
}

