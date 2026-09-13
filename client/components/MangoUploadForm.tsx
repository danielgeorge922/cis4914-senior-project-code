"use client";
import { useEffect, useRef, useState } from "react";
import ImageUploadCard from "./ImageUploadCard";
import ImageCropDialog from "./ImageCropDialog";
import ExtraFeatures from "./ExtraFeatures";

export type Photo = { id: string; name: string; url: string; kind: "fruit" | "leaf" };
const categories = [
  { kind: "fruit" as const, title: "Mango fruit", description: "Show the whole fruit, including its shape and skin color.", tip: "Try a side view and a second angle in natural light." },
  { kind: "leaf" as const, title: "Mango leaves", description: "Show the leaf shape, edges, and visible veins.", tip: "Place a leaf against a plain background with the entire leaf visible." },
];


export default function MangoUploadForm() {
  const [editing, setEditing] = useState<Photo | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(0);
  const urls = useRef(new Set<string>());
  useEffect(() => {
    const active = urls.current;
    return () => active.forEach(url => URL.revokeObjectURL(url));
  }, []);

  async function addPhotos(files: File[], kind: Photo["kind"]) {
    setPending(count => count + 1);
    setMessage("");
    const accepted: Photo[] = [];
    const errors: string[] = [];
    for (const file of files) {
      if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 10 * 1024 * 1024) {
        errors.push(`${file.name}: use a JPG, PNG, or WebP no larger than 10 MB.`);
        continue;
      }
      const url = URL.createObjectURL(file);
      try {
        const image = new window.Image();
        image.src = url;
        await image.decode();
        urls.current.add(url);
        accepted.push({ id: crypto.randomUUID(), url, name: file.name, kind });
      } catch {
        URL.revokeObjectURL(url);
        errors.push(`${file.name} could not be opened. Try another image.`);
      }
    }
    setPhotos(previous => [...previous, ...accepted]);
    setError(errors.join(" "));
    setPending(count => count - 1);
  }

  function removePhoto(photo: Photo) {
    URL.revokeObjectURL(photo.url);
    urls.current.delete(photo.url);
    setPhotos(previous => previous.filter(item => item.id !== photo.id));
    setMessage("");
  }

  return (
      <form className="mt-9 sm:mt-12" onSubmit={event => {
        event.preventDefault();
        if (photos.length && !pending) setMessage("Your images are ready. Identification is not connected yet, so no cultivar description is available. Your photos have not been sent anywhere.");
      }}>
        <div className="mb-5 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-xl font-semibold">Upload your photos</h2>
          <p className="text-sm text-gray-600">At least one fruit or leaf image</p>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          {categories.map(category => <ImageUploadCard key={category.kind} category={category} photos={photos.filter(photo => photo.kind === category.kind)} onAdd={addPhotos} onRemove={removePhoto} onEdit={setEditing} />)}
        </div>
        <ExtraFeatures />
        {editing && <ImageCropDialog photo={editing} onClose={() => setEditing(null)} onSave={blob => { const url = URL.createObjectURL(blob); urls.current.add(url); setPhotos(previous => previous.map(photo => photo.id === editing.id ? { ...photo, url } : photo)); setMessage(""); setEditing(null); }} />}
        {error && <p role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</p>}
        <div className="mt-7 flex flex-col gap-5 border-t border-gray-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p aria-live="polite" className="text-sm font-medium">{pending ? "Checking your images…" : photos.length ? `${photos.length} image${photos.length === 1 ? "" : "s"} selected` : "Add an image to get started."}</p>
            <p className="mt-1 text-xs leading-5 text-gray-500">Preview only for now. Images stay in your browser.</p>
          </div>
          <button type="submit" disabled={!photos.length || pending > 0} className="cursor-pointer min-h-12 rounded-lg bg-uf-blue px-7 py-3 font-semibold text-white transition-colors hover:bg-uf-blue/90 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-uf-blue disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-500">
            Identify mango <span aria-hidden="true" className="ml-3">→</span>
          </button>
        </div>
        {message && <p role="status" className="mt-5 rounded-lg border border-uf-blue/20 bg-uf-blue/5 p-4 text-sm leading-relaxed text-uf-blue">{message}</p>}
      </form>

  );
}
