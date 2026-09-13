import Link from "next/link";

export default function UFHeader() {
  return (
    <header className="shrink-0 border-b-4 border-uf-orange bg-uf-blue text-uf-white">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:p-3 focus:text-uf-blue"
      >
        Skip to main content
      </a>
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-4 sm:px-6 sm:py-6 md:flex-row md:items-center md:justify-between md:gap-8 lg:px-8">
        <a
          href="https://www.ufl.edu/"
          className="flex min-h-11 w-fit max-w-full items-center text-base font-semibold tracking-wide underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 sm:text-lg"
        >
          University of Florida
        </a>
        <Link
          href="/"
          className="block min-h-11 min-w-0 border-t border-white/30 pt-3 focus-visible:outline-2 focus-visible:outline-offset-4 md:border-t-0 md:border-l md:pt-0 md:pl-6"
        >
          <span className="block text-lg font-semibold break-words sm:text-xl">
            Mango Identification
          </span>
          <span className="mt-1 block text-sm text-white/85">
            By Professor Jha
          </span>
        </Link>
      </div>
    </header>
  );
}
