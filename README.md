# Urdu Pop Culture — Static Site

Plain HTML/CSS. No Streamlit, no client-side framework — every page is
fully-formed HTML the moment it loads, which is what makes it SEO-friendly
and fast.

## Files

- `generate.py` — the build script. Reads feeds + your own posts/pages,
  writes plain `.html` into `docs/`.
- `feeds.json` — RSS sources per category. Edit this to add/remove sources.
- `originals/*.md` — **your own** blog posts (see below).
- `pages/*.md` — static pages: About, Contact, Privacy Policy, Terms.
- `requirements.txt` — pinned dependencies (`feedparser` for RSS, `markdown`
  for converting your `.md` posts/pages to HTML).
- `.github/workflows/rebuild.yml` — runs `generate.py` every 2 hours and
  commits the result automatically.

## Writing an Originals post

Create a new file in `originals/`, named with simple lowercase-and-hyphens
(e.g. `originals/ikka-review.md` — no spaces, no Urdu in the filename
itself, only in the content). Format:

```
---
title: آپ کی سرخی یہاں
date: 2026-07-10
category: Drama
excerpt: ایک یا دو جملوں میں مختصر تعارف — یہ سرچ رزلٹ اور کارڈ پر نظر آئے گا۔
image: https://example.com/your-photo.jpg
---

یہاں سے آپ کا مضمون شروع ہوتا ہے، عام مارک ڈاؤن میں۔ ## سے ذیلی عنوان،
**لفظ** سے بولڈ، [متن](لنک) سے لنک وغیرہ۔
```

- `category` must be one of `Movies`, `Drama`, `Music`, or `Opinion` — this
  sets the color/icon badge.
- `image` is optional — leave it blank and the tile gets a colored gradient
  instead of a blank space.
- The filename becomes the URL: `ikka-review.md` → `ikka-review.html`.

Every post you add here is picked up automatically on the next rebuild and
shows up on the new **Originals** tab. This is the part of the site most
worth investing time in — it's the only genuinely original content Google
has reason to rank you for; the aggregated pages are supporting material
around it, not the other way round.

## Static pages

`pages/about.md`, `contact.md`, `privacy.md`, `terms.md` are already
written with reasonable starting content — **but you need to personalize
them**, especially:
- `contact.md` — replace the placeholder email with a real one you check
- `about.md` — replace with your own "why this site exists" text
- `privacy.md` — update the ads/cookies section truthfully once you add
  Adsterra, AdSense, or any analytics — this is a genuine AdSense
  requirement, not just formality

These four are linked in the footer on every page (not the top nav, to keep
the main navigation focused on content).

## New RSS source

Added **Reviewit.pk** (`reviewit.pk/drama-reviews/feed/`) to the Drama
category — it's Pakistan's dedicated drama review site, a strong niche fit.
I checked a couple of other candidates (Koimoi, Brandsynario) but couldn't
confirm working feed URLs for them, so I left them out rather than add
something likely to break silently.

## Deploy / update (same as before)

1. Upload/update files in your GitHub repo, keeping the folder structure
   (`originals/`, `pages/`, `.github/workflows/rebuild.yml` all matter).
2. If this is a fresh setup: Settings → Actions → General → "Read and write
   permissions", then Settings → Pages → Deploy from branch `main`, folder
   `/docs`.
3. Actions tab → "Rebuild site" → Run workflow (manual trigger), wait ~30s.
4. Open `generate.py` and set `SITE_URL` to your real domain if you haven't.

## Design

A glossy, image-forward "showbiz magazine" look:

- **Poster-tile grid** — image-led tiles (4:3), title overlaid on the photo
  with a gradient scrim, no summary clutter in the grid itself.
- **Fixed image extraction** — most Pakistani entertainment sites are
  WordPress-based and only embed their photo inside `content:encoded`, not
  the `media:thumbnail` tag most readers check. `generate.py` scans there
  too, plus the summary HTML, for the first real `<img>`.
- **Vibrant fallback** — no-image articles get a bold category-colored
  gradient (pink/violet/teal) instead of a blank tile.
- **"Now Showing" hero + 🔥 ٹرینڈنگ ribbon** for the latest story, plus a
  scrolling ticker under the nav.
- **Originals get the same visual treatment** as aggregated news, badged
  "اوریجنل" in gold so they're clearly distinguished as house content.

Zero JavaScript required for any of this — everything is plain HTML
background-images and CSS gradients, so none of it costs SEO or load time.

## On "full articles"

I didn't reproduce full article text from the RSS sources — copying their
articles wholesale would be copyright infringement, and Google actively
penalizes duplicate/scraped content, which works directly against the SEO
goal. The Originals section is the legitimate way to get full-length,
ownable content on the site: write it yourself, and it accrues to your
site's authority instead of a takedown risk.
