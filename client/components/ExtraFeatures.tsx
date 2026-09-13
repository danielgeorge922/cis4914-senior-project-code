const features = ["Leaf length", "Leaf width", "Fruit weight", "Fruit length", "Tree age"];

export default function ExtraFeatures() {
  return (
    <section className="mt-8 rounded-2xl border border-gray-200 p-5 sm:p-6" aria-labelledby="extra-features">
      <h2 id="extra-features" className="text-xl font-semibold">
        Extra Features <span className="text-sm font-normal text-gray-500">(optional)</span>
      </h2>
      <p className="mt-2 text-sm text-gray-600">Add any details you know about the plant.</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        {features.map((feature) => (
          <label key={feature} className="text-sm">
            {feature}
            <input name={feature} placeholder="Enter value" className="mt-2 block min-h-11 w-full rounded-lg border border-gray-300 px-3" />
          </label>
        ))}
      </div>
    </section>
  );
}
