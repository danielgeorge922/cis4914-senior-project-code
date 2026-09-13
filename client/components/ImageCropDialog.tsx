"use client";
import { useEffect, useRef, useState } from "react";
import type { Photo } from "./MangoUploadForm";

export default function ImageCropDialog({ photo, onClose, onSave }: { photo: Photo; onClose: () => void; onSave: (blob: Blob) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [source, setSource] = useState<HTMLImageElement | null>(null);
  const [zoom, setZoom] = useState(1);
  const [x, setX] = useState(50);
  const [y, setY] = useState(50);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    const image = new window.Image();
    image.onload = () => setSource(image);
    image.onerror = () => setError("Unable to load this image.");
    image.src = photo.url;
    return () => { image.onload = null; image.onerror = null; element?.close(); };
  }, [photo.url]);
  function region(image: HTMLImageElement) {
    const size = Math.min(image.naturalWidth, image.naturalHeight) / zoom;
    return { size, left: (image.naturalWidth - size) * x / 100, top: (image.naturalHeight - size) * y / 100 };
  }
  useEffect(() => {
    if (!source || !canvas.current) return;
    const size = Math.min(source.naturalWidth, source.naturalHeight) / zoom;
    const left = (source.naturalWidth - size) * x / 100;
    const top = (source.naturalHeight - size) * y / 100;
    canvas.current.getContext("2d")?.drawImage(source, left, top, size, size, 0, 0, 600, 600);
  }, [source, zoom, x, y]);
  function save() {
    if (!source) return;
    setSaving(true);
    const crop = region(source);
    const output = document.createElement("canvas");
    output.width = output.height = Math.max(1, Math.round(crop.size));
    const context = output.getContext("2d");
    if (!context) { setError("Cropping is unavailable in this browser."); setSaving(false); return; }
    context.drawImage(source, crop.left, crop.top, crop.size, crop.size, 0, 0, output.width, output.height);
    output.toBlob(blob => { if (blob) onSave(blob); else { setError("Could not save the crop. Please try again."); setSaving(false); } }, "image/png");
  }
  return <dialog ref={dialog} onCancel={onClose} aria-labelledby="crop-title" className="fixed inset-0 m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg overflow-y-auto rounded-2xl bg-white p-5 backdrop:bg-black/50">
    <h2 id="crop-title" className="text-xl font-semibold text-uf-blue">Crop image</h2>
    <p className="mt-2 text-sm text-gray-600">Adjust the square crop using zoom and position. Your original stays unchanged until you save.</p>
    <canvas ref={canvas} width={600} height={600} aria-label="Preview of cropped image" className="mx-auto my-4 aspect-square w-full max-w-72 rounded-lg bg-gray-100"/>
    {[{ label: "Zoom", value: zoom, set: setZoom, min: 1, max: 4, step: .05 }, { label: "Horizontal position", value: x, set: setX, min: 0, max: 100, step: 1 }, { label: "Vertical position", value: y, set: setY, min: 0, max: 100, step: 1 }].map(control => <label key={control.label} className="mb-3 block text-sm">{control.label}<input type="range" disabled={!source || saving} min={control.min} max={control.max} step={control.step} value={control.value} onChange={event => control.set(Number(event.target.value))} className="block min-h-8 w-full accent-uf-blue"/></label>)}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    <div className="mt-4 flex flex-wrap justify-end gap-3">
      <button type="button" onClick={() => { setZoom(1); setX(50); setY(50); }} className="min-h-11 cursor-pointer rounded-lg px-3 hover:bg-gray-100">Reset</button>
      <button type="button" onClick={onClose} className="min-h-11 cursor-pointer rounded-lg px-3 hover:bg-gray-100">Cancel</button>
      <button type="button" disabled={!source || saving} onClick={save} className="min-h-11 cursor-pointer rounded-lg bg-uf-blue px-4 text-white disabled:opacity-50">{saving ? "Saving…" : "Save crop"}</button>
    </div>
  </dialog>;
}
