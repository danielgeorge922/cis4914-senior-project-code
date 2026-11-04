"use client";
import Image from "next/image";
import { useRef, useState } from "react";
import type { Photo } from "../lib/types";
import { useLanguage } from "../lib/i18n";

type Props = {
  category: {
    kind: Photo["kind"];
    title: string;
    description: string;
    tip: string;
  };
  photos: Photo[];
  onAdd: (files: File[], kind: Photo["kind"]) => Promise<void>;
  onRemove: (photo: Photo) => void;
  onSeeExample?: () => void;
};

export default function ImageUploadCard({
  category,
  photos,
  onAdd,
  onRemove,
  onSeeExample,
}: Props) {
  const { t } = useLanguage();
  const [dragging, setDragging] = useState(false);
  const depth = useRef(0);
  return (
    <section
      aria-labelledby={category.kind + "-heading"}
      className="min-w-0 rounded-2xl border border-gray-200 bg-white p-5 sm:p-6"
    >
      <div className="flex items-start justify-between gap-2">
        <h3
          id={category.kind + "-heading"}
          className="text-lg font-semibold text-uf-blue"
        >
          {category.title}
        </h3>
        {onSeeExample && (
          <button
            type="button"
            onClick={onSeeExample}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-uf-blue hover:bg-blue-100 transition-colors"
          >
            <span>{t("seeExample")}</span>
            <span aria-hidden="true">👁️</span>
          </button>
        )}
      </div>
      <p className="mt-2 min-h-12 text-sm leading-6 text-gray-600">
        {category.description}
      </p>
      <label
        className={`relative mt-5 flex min-h-48 cursor-pointer flex-col items-center justify-center rounded-xl px-4 py-7 text-center transition-colors focus-within:outline-2 focus-within:outline-offset-4 focus-within:outline-uf-blue ${dragging ? "bg-blue-100 ring-2 ring-uf-blue" : "bg-gray-50 hover:bg-gray-100"}`}
        onDragEnter={(event) => {
          event.preventDefault();
          if (event.dataTransfer.types.includes("Files")) {
            depth.current++;
            setDragging(true);
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          event.dataTransfer.dropEffect = "copy";
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          depth.current = Math.max(0, depth.current - 1);
          if (!depth.current) setDragging(false);
        }}
        onDrop={(event) => {
          event.preventDefault();
          depth.current = 0;
          setDragging(false);
          void onAdd(Array.from(event.dataTransfer.files), category.kind);
        }}
      >
        <input
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          aria-label={`Upload ${category.title.toLowerCase()} photos`}
          onChange={(event) => {
            const files = Array.from(event.target.files ?? []);
            event.target.value = "";
            void onAdd(files, category.kind);
          }}
        />
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          aria-hidden="true"
          className="mb-4 h-8 w-8 text-uf-blue"
        >
          <path d="M12 16V3m-5 5 5-5 5 5M4 15v5h16v-5" />
        </svg>
        <span className="font-semibold text-uf-blue">
          {dragging ? t("chooseImages") : t("chooseImages")}
        </span>
        <span className="mt-1 text-sm text-gray-600">
          {dragging ? t("dragDrop") : t("dragDrop")}
        </span>
        <span className="mt-3 text-xs text-gray-500">
          {t("fileLimits")}
        </span>
      </label>
      <p className="mt-4 text-xs leading-5 text-gray-600">{category.tip}</p>
      <ul className="mt-4 space-y-3">
        {photos.map((photo) => (
          <li
            key={photo.id}
            className="flex min-w-0 items-center gap-3 rounded-lg bg-gray-50 p-2"
          >
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <Image
                src={photo.url}
                alt=""
                width={56}
                height={56}
                unoptimized
                className="h-14 w-14 shrink-0 rounded-md object-cover"
              />
              <span className="min-w-0">
                <span className="block truncate text-sm">{photo.name}</span>
              </span>
            </div>
            <button
              type="button"
              onClick={() => onRemove(photo)}
              aria-label={`Remove ${photo.name}`}
              className="flex min-h-11 min-w-11 cursor-pointer items-center justify-center rounded-md text-xl text-gray-600 hover:bg-gray-200"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
