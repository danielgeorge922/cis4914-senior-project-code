"use client";
import Image from "next/image";
import { useEffect } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  viewType: "exterior" | "interior";
};

export default function ExampleModal({ isOpen, onClose, viewType }: Props) {
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

  if (!isOpen) return null;

  const isExterior = viewType === "exterior";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white p-6 shadow-2xl transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div>
            <span className="text-xs font-semibold tracking-wider text-uf-orange uppercase">
              Photo Guide
            </span>
            <h3 id="modal-title" className="text-xl font-bold text-uf-blue">
              {isExterior ? "Exterior View (Whole Fruit)" : "Interior View (Cut Fruit)"}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
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

        <p className="mt-2 text-sm leading-relaxed text-gray-600">
          {isExterior
            ? "Place the whole, intact mango against a neutral surface with natural, indirect lighting. Capture the overall fruit silhouette and skin coloration."
            : "Slice the fruit lengthwise through the cheek to show the flesh coloration, fiber density, and stone/seed shape."}
        </p>

        <div className="relative mt-4 aspect-4/3 w-full overflow-hidden rounded-xl bg-gray-100 border border-gray-200">
          <Image
            src={isExterior ? "/examples/exterior-example.jpg" : "/examples/interior-example.jpg"}
            alt={isExterior ? "Sample exterior mango photograph" : "Sample cut-open mango photograph"}
            fill
            className="object-contain"
          />
        </div>

        <ul className="mt-4 space-y-1.5 text-xs text-gray-600">
          <li className="flex items-center gap-1.5">
            <span className="text-uf-blue font-bold">✓</span>
            {isExterior
              ? "Ensure the entire fruit is in the frame with good focus"
              : "Expose clean internal flesh without heavy shadows"}
          </li>
          <li className="flex items-center gap-1.5">
            <span className="text-uf-blue font-bold">✓</span>
            Avoid cluttered backgrounds or fingers covering the fruit
          </li>
        </ul>

        <button
          type="button"
          onClick={onClose}
          className="mt-5 w-full rounded-xl bg-uf-blue py-3 text-sm font-semibold text-white shadow-sm hover:bg-uf-blue/90 transition-colors"
        >
          Got it
        </button>
      </div>
    </div>
  );
}
