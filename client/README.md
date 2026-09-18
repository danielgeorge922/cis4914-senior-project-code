# Mango Identification

Next.js App Router frontend for Professor Jha's mango identification project. The current experience is a local prototype; no model or backend is connected.

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
- `/processing`: animated mango and simulated progress, followed by automatic navigation.
- `/predictions-result`: a primary prediction and nine alternatives from mock data.

## Code organization

- `app/`: routes, shared layout, global styles, and processing animation styles.
- `components/`: upload form, upload cards, optional features, prediction cards, score ring, and UF header/footer.
- `lib/types.ts`: shared photo and prediction types.
- `lib/const.ts`: mock prediction response and simulated processing duration.
- `public/`: static assets, including the placeholder mango illustration.

The upload form owns photo state; the optional feature section owns its own rows. Features and uploaded photos are not sent to an API. Image object URLs are local to the upload form; submissions are not persisted across reloads. Results use the same illustrative fixture regardless of the uploaded images.

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

Predictions, scores, descriptions, and cultivar imagery are placeholders. Processing is a timer, not inference. The server and model directories outside this client are reserved for future implementation.
