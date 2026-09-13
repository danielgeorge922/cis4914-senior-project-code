import MangoUploadForm from "../components/MangoUploadForm";

export default function Home() {
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8"
    >
      <div className="max-w-3xl">
        <p className="mb-3 text-sm font-semibold tracking-widest text-uf-blue uppercase">
          Mango identification
        </p>
        <h1 className="text-3xl leading-tight font-semibold tracking-tight text-uf-blue sm:text-4xl lg:text-5xl">
          Get to know your mango.
        </h1>
        <p className="mt-5 max-w-2xl text-base leading-relaxed text-gray-700 sm:text-lg">
          Upload photos of a mango fruit, its leaves, or both to help identify
          its cultivar and learn about its characteristics.
        </p>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-gray-600">
          Identification is an estimate, not a guarantee. Clear photos from
          multiple angles provide more useful visual details.
        </p>
      </div>
      <MangoUploadForm />
    </main>
  );
}
