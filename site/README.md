# The docs site

For Jeremy. This folder is the landing page and the docs pages of sg-mockgun. The design is yours to
change. The facts are not: they come from `README.md` and `docs/` at the repo root.

## Run it

Requires node 22.

```sh
cd site
npm install
npm run dev
```

Open http://localhost:5173/. Edits reload in place.

## Where things are

| path | what |
|---|---|
| `src/app.css` | Tokens: colours, type, radius, gutter, page width, band spacing, easing. Start here. |
| `src/routes/+page.svelte` | The landing page, one section per `<section>`, styles at the bottom of the file. |
| `src/routes/docs/` | The docs pages, one folder each, sharing `+layout.svelte`. |
| `src/lib/content/*.md` | The text of each docs page, rendered by `src/lib/markdown.js`. |
| `src/lib/Nav.svelte`, `Footer.svelte` | Nav and footer. |
| `src/lib/site.js` | Links and the list of docs pages. |
| `src/lib/seo.js` | The canonical origin, the sitemap, `robots.txt`, `llms.txt`. |
| `static/fonts/` | Geist and Geist Mono, self-hosted. |

## Rules that must pass

- `npm run check` passes (svelte-check).
- `npm run build` passes.

## Rules that nothing checks

- No analytics, no tracking, no consent banner.
- No request to a third party at runtime: no external fonts, scripts, images or embeds.
- Dark only. There is no light scheme and no toggle.
- No horizontal scroll at 375px.
- Copy follows `CLAUDE.md` in sg-comfyui, section Writing. Short, exact, no selling, no em dashes.
  Change the words with Kevin.

## Captures

Run after `npm run build`. It needs `npm i --no-save playwright` once.

```sh
npm run shots
```

It serves `build/` and writes screenshots to `site/shots/` (gitignored). `shots/landing.png` is the
card sg-suite shows. A request to another host, or a horizontal scroll, fails the run.

## Ship

Branch off `dev`. Open a pull request onto `dev`. Kevin merges. Vercel deploys `main` only
(`vercel.json`), at https://sg-mockgun.vercel.app.
