# Mango Identification

Next.js App Router frontend for Professor Jha's mango identification project. It sends photos to the API in `../server` (default `http://localhost:8080`, override with `NEXT_PUBLIC_API_URL`).

## Development

From this directory:

```sh
npm install
npm run dev
```

Open http://localhost:3000.

Checks: `npm run lint` and `npx tsc --noEmit`.
Production: `npm run build`, then `npm start`.

## Routes

- `/`: fruit/leaf uploads, image previews, and optional plant features.
- `/processing`: animated mango while the API request runs; shows an error if it fails.
- `/predictions-result`: the top match and nine alternatives returned by the API.

## Code organization

- `app/`: routes, shared layout, global styles, and processing animation styles.
- `components/`: upload form, upload cards, optional features, prediction cards, score ring, and UF header/footer.
- `lib/types.ts`: shared photo and prediction types.
- `lib/api.ts`: sends photos to the API and holds the result between pages.
- `lib/const.ts`: expected processing time for the progress bar.
- `public/`: static assets, including the placeholder mango illustration.

The upload form owns photo state; the optional feature section owns its own rows and is not sent to the API. Results live in memory, so reloading the results page clears them.

## Styling

Tailwind CSS v4 with UF aliases defined in `app/globals.css`:

- `bg-uf-blue`, `text-uf-blue`: #0021A5.
- `bg-uf-orange`, `border-uf-orange`: #FA4616.
- `text-uf-white`: #FFFFFF.
- `font-sans`: IBM Plex Sans (default).
- `font-serif`: Source Serif 4.
- `font-display`: Anybody.

Fonts load through Google Fonts. The header currently uses text identification rather than an approved UF logo asset.

## Prototype limitations

Until trained models exist, the API runs in mock mode and the results page shows a "Demo results" notice. Cultivar descriptions and imagery are placeholders.
