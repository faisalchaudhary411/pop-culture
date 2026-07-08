# Urdu Pop Culture — Static Site (SEO-friendly version)

Plain HTML/CSS. No Streamlit, no client-side framework, nothing for Google
to wait around for — every page is fully-formed HTML the moment it loads.

## How it works

1. `generate.py` reads `feeds.json`, fetches each RSS feed, and writes plain
   `.html` files into `docs/` (`index.html`, `movies.html`, `drama.html`,
   `music.html`), plus `style.css`, `sitemap.xml`, and `robots.txt`.
2. A GitHub Action (`.github/workflows/rebuild.yml`) runs `generate.py`
   automatically every 2 hours, and commits the refreshed `docs/` folder.
   You never need to run anything yourself from a PC.
3. GitHub Pages serves the `docs/` folder as your live site, and you point
   Cloudflare at it exactly like you did for FileDesk.

## One-time setup (all from your phone, GitHub web editor)

1. Create a new GitHub repo, upload these files, keeping the folder
   structure: `generate.py`, `feeds.json`, `.github/workflows/rebuild.yml`.
2. Open `generate.py` and change `SITE_URL = "https://example.com"` at the
   top to your real domain (e.g. `https://urdu.yourdomain.com`) — this feeds
   into canonical tags and the sitemap, both of which matter for SEO.
3. In repo Settings → Pages, set Source to "Deploy from a branch", branch
   `main`, folder `/docs`.
4. In repo Settings → Actions → General, under "Workflow permissions",
   select "Read and write permissions" — the Action needs this to commit
   the generated files back.
5. Go to the Actions tab and manually run "Rebuild site" once (via
   "Run workflow") to generate the first version of `docs/`.
6. Add your Cloudflare CNAME pointing at `<username>.github.io`, same
   pattern as `tools.voxcraft.site`.

After that, it updates itself every 2 hours with no further action from you.

## Editing content sources

Edit `feeds.json` only — never hand-edit anything inside `docs/`, since
the next scheduled run overwrites it. Each edit to `feeds.json` also
triggers an immediate rebuild (see the `push` trigger in the workflow).

## Verifying feed URLs

I confirmed these feed URLs exist from search results, but couldn't
live-fetch them from this sandbox (no internet access to news sites here) —
open each once in a browser to confirm you get raw XML back, not a 404:
- `https://www.pakshowbiz.com/feed`
- `https://www.bollywoodhungama.com/feed`
- `https://urdu.arynews.tv/feed`

If one is dead, swap it out in `feeds.json` — most sites expose a feed at
`/feed` or `/rss.xml`, or search "[site name] RSS feed feedspot" to find one.

## Design

Built around a cinema/theater concept rather than a generic news-list look:
- A marquee-style header (gold border with a dotted "lightbulb" edge)
- A scrolling breaking-headlines ticker under the nav
- A "Now Showing" hero section for the single latest story
- Cards styled as torn ticket stubs, each with a color-coded genre stamp
  (gold = Movies, rose = Drama, teal = Music) and a "تازہ" (fresh) badge
  on anything published in the last 3 hours

All of this is still plain HTML/CSS — no JS is required for any of it, so
none of it costs you SEO or load time. The only animation (the ticker) also
respects `prefers-reduced-motion` and its content exists as normal links
either way, so nothing depends on JS running for a visitor or a crawler.

## Why this is better for SEO/speed than the Streamlit version

- Streamlit ships a full Python-in-the-browser app shell before any content
  appears — slow first paint, and Google's crawler often sees an empty
  `<div id="root">` rather than your actual headlines.
- This version is server-generated ahead of time: the HTML Google (and the
  visitor) receives already contains every headline, image, and link.
- `sitemap.xml` + `robots.txt` are generated automatically so search engines
  can discover all four pages immediately.

## Monetization later

Same advice as before — if you add Adsterra, keep it to one contained
banner `<div>` in the template rather than Social Bar/popup scripts.
