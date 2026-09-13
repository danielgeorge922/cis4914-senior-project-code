export default function UFFooter() {
  return (
    <footer className="mt-auto shrink-0 bg-uf-blue text-uf-white">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6 sm:py-8 lg:flex-row lg:items-center lg:justify-between lg:gap-8 lg:px-8">
        <div className="min-w-0">
          <p className="text-lg font-semibold">Mango Identification</p>
          <p className="mt-1 text-sm text-white/85">
            Professor Jha · University of Florida
          </p>
        </div>
        <nav
          aria-label="University resources"
          className="flex flex-col items-start gap-x-6 text-sm sm:flex-row sm:flex-wrap sm:items-center [&>a]:inline-flex [&>a]:min-h-11 [&>a]:items-center"
        >
          <a
            className="underline underline-offset-4 hover:text-white/80 focus-visible:outline-2 focus-visible:outline-offset-4"
            href="https://www.ufl.edu/"
          >
            University of Florida
          </a>
          <a
            className="underline underline-offset-4 hover:text-white/80 focus-visible:outline-2 focus-visible:outline-offset-4"
            href="https://accessibility.ufl.edu/"
          >
            Accessibility
          </a>
          <a
            className="underline underline-offset-4 hover:text-white/80 focus-visible:outline-2 focus-visible:outline-offset-4"
            href="https://privacy.ufl.edu/"
          >
            Privacy
          </a>
        </nav>
      </div>
    </footer>
  );
}
