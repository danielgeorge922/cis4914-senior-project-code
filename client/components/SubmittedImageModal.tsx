"use client";
import { useEffect } from "react";
import type { SubmittedPhoto } from "../lib/types";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  photos: SubmittedPhoto[];
};

export default function SubmittedImageModal({ isOpen, onClose, photos }: Props) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen || !photos.length) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="submitted-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl transition-all sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between pb-3 border-b border-gray-100">
          <div>
            <span className="text-xs font-semibold tracking-wider text-uf-orange uppercase">
              Inference Input
            </span>
            <h3 id="submitted-modal-title" className="text-xl font-bold text-uf-blue">
              {photos.length === 1 ? "Your Uploaded Photo" : "Your Uploaded Photos"}
            </h3>
            <p className="mt-1 text-xs text-gray-500">
              The exact image{photos.length > 1 ? "s" : ""} evaluated by the neural network classifier.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-700 transition-colors"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="mt-6 space-y-6">
          {photos.map((photo, index) => {
            const isInterior = photo.kind === "interior";
            return (
              <div
                key={index}
                className="overflow-hidden rounded-2xl border border-gray-200 bg-gray-50"
              >
                <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2.5">
                  <span className="text-xs font-semibold text-gray-700 truncate max-w-xs">
                    {photo.name || `Photo #${index + 1}`}
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      isInterior
                        ? "bg-amber-100 text-amber-800"
                        : "bg-blue-100 text-uf-blue"
                    }`}
                  >
                    {isInterior ? "Interior View" : "Exterior View"}
                  </span>
                </div>
                <div className="relative flex items-center justify-center p-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={photo.dataUrl}
                    alt={photo.name || "Submitted mango photo"}
                    className="max-h-[60vh] w-auto max-w-full rounded-xl object-contain shadow-xs"
                  />
                </div>
              </div>
            );
          })}
        </div>

        <button
          type="button"
          onClick={onClose}
          className="mt-6 w-full rounded-xl bg-uf-blue py-3 text-sm font-semibold text-white shadow-sm hover:bg-uf-blue/90 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
}
