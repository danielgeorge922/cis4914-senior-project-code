"use client";
import { useEffect, useRef, useState } from "react";

const options = ["Leaf length", "Leaf width", "Fruit weight", "Fruit length", "Tree age"];
type Row = { id: string; feature: string; value: string };

function FeaturePicker({ row, rows, onChange }: { row: Row; rows: Row[]; onChange: (feature: string) => void }) {
  const [open, setOpen] = useState(!row.feature);
  const root = useRef<HTMLDivElement>(null);
  const first = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (open) first.current?.focus();
    function dismiss(event: PointerEvent) { if (!root.current?.contains(event.target as Node)) setOpen(false); }
    document.addEventListener("pointerdown", dismiss);
    return () => document.removeEventListener("pointerdown", dismiss);
  }, [open]);
  const available = options.find(option => !rows.some(other => other.id !== row.id && other.feature === option));
  return <div ref={root} className="relative flex-1" onKeyDown={event => { if (event.key === "Escape") { setOpen(false); root.current?.querySelector("button")?.focus(); } }}>
    <button type="button" aria-expanded={open} aria-controls={row.id + "-options"} onClick={() => setOpen(!open)} className="min-h-11 w-full cursor-pointer rounded-lg border border-gray-300 bg-white px-3 text-left">{row.feature || "Select a feature"} <span aria-hidden="true">▾</span></button>
    {open && <div id={row.id + "-options"} className="absolute top-full z-10 mt-1 w-full rounded-lg border border-gray-200 bg-white p-1 shadow-lg">
      {options.map(option => { const taken = rows.some(other => other.id !== row.id && other.feature === option);
        return <button ref={option === available ? first : undefined} type="button" key={option} disabled={taken} onClick={() => { onChange(option); setOpen(false); root.current?.querySelector("button")?.focus(); }} className="block min-h-11 w-full cursor-pointer rounded px-3 text-left text-sm hover:bg-gray-100 disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-400">{option}{taken ? " — already selected" : ""}</button>;
      })}
    </div>}
  </div>;
}

export default function ExtraFeatures() {
  const [rows, setRows] = useState<Row[]>([]);
  return <section className="mt-8 rounded-2xl border border-gray-200 p-5 sm:p-6" aria-labelledby="extra-features">
    <div className="flex items-center justify-between gap-3"><h2 id="extra-features" className="text-xl font-semibold">Extra Features <span className="text-sm font-normal text-gray-500">(optional)</span></h2>
      <button type="button" disabled={rows.length === options.length} aria-label="Add an extra feature" onClick={() => setRows(previous => [...previous, { id: crypto.randomUUID(), feature: "", value: "" }])} className="min-h-11 min-w-11 cursor-pointer rounded-lg bg-uf-blue text-2xl text-white hover:bg-uf-blue/90 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-500">+</button>
    </div>
    <p className="mt-2 text-sm text-gray-600">Add any details you know about the plant. Each feature can be selected once.</p>
    <div className="mt-4 space-y-3">{rows.map(row => <div key={row.id} className="flex flex-wrap items-start gap-3">
      <FeaturePicker row={row} rows={rows} onChange={feature => setRows(previous => previous.map(other => other.id === row.id ? { ...other, feature } : other))}/>
      <input aria-label={row.feature ? row.feature + " value" : "Feature value"} placeholder="Enter value" value={row.value} onChange={event => setRows(previous => previous.map(other => other.id === row.id ? { ...other, value: event.target.value } : other))} className="min-h-11 w-32 flex-1 rounded-lg border border-gray-300 px-3" />
      <button type="button" aria-label={`Remove ${row.feature || "extra feature"}`} onClick={() => setRows(previous => previous.filter(other => other.id !== row.id))} className="min-h-11 min-w-11 cursor-pointer rounded-lg text-xl hover:bg-gray-100">×</button>
    </div>)}</div>
  </section>;
}
