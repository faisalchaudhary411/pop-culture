"""
Static site generator for the Urdu Pop Culture aggregator.

Run automatically by GitHub Actions on a schedule. Writes plain .html
files into docs/ — no JS framework, fully pre-rendered, so search engines
see complete content immediately.

Edit feeds.json to add/remove sources. Do not hand-edit docs/ — it is
regenerated every run.
"""
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import feedparser

SITE_NAME = "اردو تفریح"
SITE_NAME_EN = "Urdu Pop Culture"
SITE_URL = "https://example.com"  # TODO: replace with your real domain
SITE_TAGLINE = "آج کی تازہ خبریں — فلم، ڈرامہ اور موسیقی"
SITE_DESCRIPTION = "Latest Urdu & Pakistani entertainment news: movies, drama and music, aggregated from verified sources."
OUT_DIR = Path(__file__).parent / "docs"
FEEDS_FILE = Path(__file__).parent / "feeds.json"
MAX_ITEMS_PER_CATEGORY = 40
BREAKING_HOURS = 3  # items newer than this get a "تازہ" badge

# Each category gets its own accent color + Urdu label + genre-stamp icon.
CATEGORY_META = {
    "Movies": {"urdu": "فلمیں", "color": "#d4a24c", "stamp": "🎬"},
    "Drama":  {"urdu": "ڈرامہ", "color": "#c1485a", "stamp": "🎭"},
    "Music":  {"urdu": "موسیقی", "color": "#4a9d8f", "stamp": "🎵"},
}


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_summary(raw_html, max_len=200):
    text = re.sub(r"<[^>]+>", "", raw_html or "")
    text = html.unescape(text).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return html.escape(text)


def parse_date(entry):
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def extract_image(entry):
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key)
        if media and isinstance(media, list):
            url = media[0].get("url")
            if url:
                return url
    for link in entry.get("links", []):
        if link.get("type", "").startswith("image"):
            return link.get("href")
    return None


def fetch_feed(name, url, category):
    items = []
    try:
        parsed = feedparser.parse(url, request_headers={
            "User-Agent": "Mozilla/5.0 (compatible; UrduPopCultureBot/1.0)"
        })
        for e in parsed.entries[:MAX_ITEMS_PER_CATEGORY]:
            items.append({
                "title": html.escape(e.get("title", "").strip()),
                "link": e.get("link", ""),
                "summary": clean_summary(e.get("summary", "") or e.get("description", "")),
                "published": parse_date(e),
                "source": name,
                "domain": urlparse(url).netloc.replace("www.", ""),
                "image": extract_image(e),
                "category": category,
            })
    except Exception as ex:
        print(f"  ! failed to fetch {name} ({url}): {ex}")
    return items


def fetch_category(category, feeds_dict):
    all_items = []
    for name, url in feeds_dict.items():
        print(f"  fetching {name}...")
        all_items.extend(fetch_feed(name, url, category))
    all_items.sort(
        key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return all_items


def is_breaking(item):
    if not item["published"]:
        return False
    age_hours = (datetime.now(timezone.utc) - item["published"]).total_seconds() / 3600
    return age_hours <= BREAKING_HOURS


def time_ago(dt):
    if not dt:
        return ""
    hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    if hours < 1:
        return "ابھی ابھی"
    if hours < 24:
        return f"{int(hours)} گھنٹے پہلے"
    return f"{int(hours / 24)} دن پہلے"


def render_hero(item):
    """The 'Now Showing' marquee feature for the single most recent story."""
    meta = CATEGORY_META.get(item["category"], {"color": "#d4a24c", "urdu": item["category"], "stamp": "★"})
    img_style = f'style="background-image:url(\'{item["image"]}\')"' if item["image"] else ""
    breaking = '<span class="hero-badge">تازہ خبر</span>' if is_breaking(item) else ""
    return f"""
    <section class="hero" {img_style}>
      <div class="hero-overlay">
        <span class="hero-eyebrow" style="--stamp-color:{meta['color']}">اب دکھایا جا رہا ہے · {meta['stamp']} {meta['urdu']}</span>
        {breaking}
        <h1 class="hero-title"><a href="{item['link']}" target="_blank" rel="noopener nofollow">{item['title']}</a></h1>
        <p class="hero-summary">{item['summary']}</p>
        <div class="hero-meta">{item['source']} · {time_ago(item['published'])}</div>
      </div>
    </section>"""


def render_card(item):
    meta = CATEGORY_META.get(item["category"], {"color": "#d4a24c", "urdu": item["category"], "stamp": "★"})
    img_tag = f'<img src="{item["image"]}" alt="" loading="lazy" width="160" height="110">' if item["image"] else \
        f'<div class="card-noimg" style="--stamp-color:{meta["color"]}">{meta["stamp"]}</div>'
    date_str = item["published"].strftime("%d %b") if item["published"] else ""
    breaking = '<span class="badge-breaking">تازہ</span>' if is_breaking(item) else ""
    return f"""
    <article class="ticket">
      <div class="ticket-image">{img_tag}</div>
      <div class="ticket-perf"></div>
      <div class="ticket-body">
        <div class="ticket-meta">
          <span class="genre-stamp" style="--stamp-color:{meta['color']}">{meta['stamp']} {meta['urdu']}</span>
          {breaking}
        </div>
        <h2><a href="{item['link']}" target="_blank" rel="noopener nofollow">{item['title']}</a></h2>
        <p class="summary">{item['summary']}</p>
        <div class="ticket-footer">{item['source']} {('· ' + date_str) if date_str else ''}</div>
      </div>
    </article>"""


NAV_ITEMS = [
    ("index.html", "سب کچھ", "All"),
    ("movies.html", "فلمیں", "Movies"),
    ("drama.html", "ڈرامہ", "Drama"),
    ("music.html", "موسیقی", "Music"),
]


def render_nav(active_file):
    tabs = []
    for fname, urdu, eng in NAV_ITEMS:
        cls = " active" if fname == active_file else ""
        tabs.append(f'<a class="tab{cls}" href="{fname}"><span class="tab-urdu">{urdu}</span><span class="tab-en">{eng}</span></a>')
    return "\n".join(tabs)


def render_ticker(headlines):
    """A slow-moving marquee strip of the latest headlines under the header.
    Content is duplicated in a plain <noscript>-safe list too, so it's
    identical whether or not the CSS animation runs (reduced-motion safe)."""
    items = "".join(f'<a href="{h["link"]}" target="_blank" rel="noopener nofollow">{h["title"]}</a><span class="dot">•</span>' for h in headlines)
    return f'<div class="ticker"><div class="ticker-track">{items}{items}</div></div>'


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ur" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<meta name="description" content="{page_description}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="{page_description}">
<meta property="og:url" content="{canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <div class="marquee-frame">
    <h1 class="brand"><a href="index.html">{site_name}<span class="brand-en">{site_name_en}</span></a></h1>
    <p class="tagline">{tagline}</p>
  </div>
  <nav class="tabs">{nav}</nav>
</header>
{ticker}
<main>
{hero}
<div class="grid">
{cards}
</div>
</main>
<footer>
  <p>مواد اصل ذرائع کے پبلک RSS فیڈز سے اکٹھا کیا گیا ہے — مکمل مضامین یہاں شائع نہیں کیے جاتے۔</p>
  <p class="footer-en">Content aggregated from public RSS feeds of original publishers. Headlines link to source; full articles are not reproduced.</p>
  <p class="updated">Last updated: {updated}</p>
</footer>
</body>
</html>"""


def build():
    OUT_DIR.mkdir(exist_ok=True)
    feeds = load_feeds()
    updated = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    category_items = {}
    for category, feed_dict in feeds.items():
        print(f"Category: {category}")
        category_items[category] = fetch_category(category, feed_dict)

    all_items = []
    for items in category_items.values():
        all_items.extend(items)
    all_items.sort(
        key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    pages = {"index.html": ("All", all_items)}
    slug_map = {"Movies": "movies.html", "Drama": "drama.html", "Music": "music.html"}
    for category, items in category_items.items():
        fname = slug_map.get(category, f"{category.lower()}.html")
        pages[fname] = (category, items)

    for fname, (category, items) in pages.items():
        if items:
            hero_html = render_hero(items[0])
            rest = items[1:]
        else:
            hero_html = ""
            rest = []

        ticker_html = render_ticker(all_items[:8]) if fname == "index.html" and all_items else ""

        cards_html = "\n".join(render_card(it) for it in rest) or \
            ('' if items else '<p class="empty">فی الحال کوئی خبر دستیاب نہیں<br><span>Feeds temporarily unavailable — check back shortly.</span></p>')

        page = PAGE_TEMPLATE.format(
            page_title=f"{CATEGORY_META.get(category, {}).get('urdu', category)} — {SITE_NAME} | {SITE_NAME_EN}" if category != "All" else f"{SITE_NAME} | {SITE_NAME_EN}",
            page_description=f"Latest {category} news: {SITE_DESCRIPTION}" if category != "All" else SITE_DESCRIPTION,
            canonical=f"{SITE_URL}/{fname}",
            site_name=SITE_NAME,
            site_name_en=SITE_NAME_EN,
            tagline=SITE_TAGLINE,
            nav=render_nav(fname),
            ticker=ticker_html,
            hero=hero_html,
            cards=cards_html,
            updated=updated,
        )
        (OUT_DIR / fname).write_text(page, encoding="utf-8")
        print(f"  wrote {fname} ({len(items)} items)")

    write_static_assets()
    write_sitemap(pages.keys())
    print("Done.")


def write_static_assets():
    (OUT_DIR / "style.css").write_text(CSS, encoding="utf-8")
    (OUT_DIR / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8"
    )


def write_sitemap(filenames):
    urls = "\n".join(f"  <url><loc>{SITE_URL}/{f}</loc></url>" for f in filenames)
    sitemap = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>'
    (OUT_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&family=Fraunces:ital,wght@0,600;1,500&family=Archivo:wght@400;600;700&display=swap');

:root {
  --bg: #1a0f14;
  --surface: #241318;
  --surface-raised: #2c171d;
  --gold: #d4a24c;
  --rose: #c1485a;
  --teal: #4a9d8f;
  --cream: #f3e9dc;
  --muted: #a98f8a;
  --hairline: #3a2229;
}

* { box-sizing: border-box; }

@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--cream);
  font-family: 'Noto Nastaliq Urdu', serif;
}
a { color: inherit; }
a:focus-visible, button:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }

/* ---------- Header: cinema marquee ---------- */
.site-header {
  text-align: center;
  padding: 2rem 1rem 0;
  background:
    radial-gradient(ellipse at top, rgba(212,162,76,0.15), transparent 60%),
    var(--bg);
  border-bottom: 1px solid var(--hairline);
}
.marquee-frame {
  display: inline-block;
  padding: 1rem 2rem;
  border: 2px solid var(--gold);
  border-radius: 6px;
  position: relative;
}
.marquee-frame::before, .marquee-frame::after {
  content: "";
  position: absolute;
  top: -6px; bottom: -6px;
  width: 6px;
  background-image: radial-gradient(circle, var(--gold) 2.5px, transparent 2.6px);
  background-size: 12px 16px;
  background-repeat: repeat-y;
}
.marquee-frame::before { left: -14px; }
.marquee-frame::after { right: -14px; }

.brand a { text-decoration: none; }
.brand {
  font-family: 'Fraunces', serif;
  font-style: italic;
  font-weight: 600;
  font-size: 2.1rem;
  color: var(--gold);
  margin: 0;
  letter-spacing: 0.02em;
}
.brand-en {
  display: block;
  font-family: 'Archivo', sans-serif;
  font-style: normal;
  font-size: 0.7rem;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--muted);
  margin-top: 0.25rem;
}
.tagline {
  font-size: 0.95rem;
  color: var(--muted);
  margin: 0.8rem 0 0;
}

.tabs {
  display: flex;
  justify-content: center;
  gap: 0;
  margin-top: 1.5rem;
  border-bottom: 1px solid var(--hairline);
  overflow-x: auto;
}
.tab {
  font-family: 'Archivo', sans-serif;
  text-decoration: none;
  color: var(--muted);
  padding: 0.9rem 1.4rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  border-bottom: 3px solid transparent;
  white-space: nowrap;
}
.tab-urdu { font-family: 'Noto Nastaliq Urdu', serif; font-size: 1.1rem; }
.tab-en { font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.1em; }
.tab.active, .tab:hover { color: var(--gold); border-bottom-color: var(--gold); }

/* ---------- Ticker ---------- */
.ticker {
  background: var(--surface);
  border-bottom: 1px solid var(--hairline);
  overflow: hidden;
  white-space: nowrap;
  padding: 0.6rem 0;
}
.ticker-track {
  display: inline-block;
  animation: scroll-rtl 45s linear infinite;
  font-family: 'Archivo', sans-serif;
  font-size: 0.85rem;
}
.ticker-track a { text-decoration: none; color: var(--cream); margin-inline-end: 0.6rem; }
.ticker-track a:hover { color: var(--gold); }
.ticker .dot { color: var(--rose); margin-inline-end: 0.6rem; }
@keyframes scroll-rtl {
  from { transform: translateX(0); }
  to { transform: translateX(50%); }
}

/* ---------- Hero: Now Showing ---------- */
.hero {
  position: relative;
  min-height: 320px;
  border-radius: 14px;
  margin: 1.5rem 1rem 0;
  background-size: cover;
  background-position: center;
  background-color: var(--surface-raised);
  overflow: hidden;
  display: flex;
  align-items: flex-end;
}
.hero-overlay {
  width: 100%;
  padding: 2rem 1.5rem 1.5rem;
  background: linear-gradient(to top, rgba(15,8,10,0.95) 20%, rgba(15,8,10,0.4) 70%, transparent);
}
.hero-eyebrow {
  display: inline-block;
  font-family: 'Archivo', sans-serif;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: var(--stamp-color, var(--gold));
  border: 1px solid var(--stamp-color, var(--gold));
  border-radius: 20px;
  padding: 0.25rem 0.8rem;
  margin-bottom: 0.8rem;
}
.hero-badge {
  display: inline-block;
  font-family: 'Archivo', sans-serif;
  font-size: 0.7rem;
  background: var(--rose);
  color: #fff;
  padding: 0.25rem 0.7rem;
  border-radius: 20px;
  margin-inline-start: 0.5rem;
  margin-bottom: 0.8rem;
}
.hero-title { margin: 0 0 0.6rem; font-size: 1.7rem; line-height: 1.8; }
.hero-title a { text-decoration: none; }
.hero-title a:hover { color: var(--gold); }
.hero-summary { color: #d9c9c0; font-size: 1.05rem; line-height: 1.9; max-width: 60ch; margin: 0 0 0.8rem; }
.hero-meta { font-family: 'Archivo', sans-serif; font-size: 0.8rem; color: var(--muted); }

/* ---------- Ticket-stub cards ---------- */
main { max-width: 920px; margin: 0 auto; padding: 0 1rem 2rem; }
.grid { display: grid; gap: 1.1rem; margin-top: 1.5rem; }

.ticket {
  display: flex;
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}
.ticket-image { width: 150px; flex-shrink: 0; background: var(--surface-raised); }
.ticket-image img { width: 100%; height: 100%; object-fit: cover; display: block; }
.card-noimg {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  font-size: 2rem;
  color: var(--stamp-color, var(--gold));
  min-height: 120px;
}
.ticket-perf {
  width: 0;
  border-inline-start: 2px dashed var(--hairline);
  position: relative;
}
.ticket-perf::before, .ticket-perf::after {
  content: "";
  position: absolute;
  width: 14px; height: 14px;
  background: var(--bg);
  border-radius: 50%;
  inset-inline-start: -8px;
}
.ticket-perf::before { top: -7px; }
.ticket-perf::after { bottom: -7px; }
.ticket-body { padding: 1rem 1.2rem; flex: 1; min-width: 0; }
.ticket-meta { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
.genre-stamp {
  font-family: 'Archivo', sans-serif;
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  color: var(--stamp-color, var(--gold));
  border: 1px solid var(--stamp-color, var(--gold));
  border-radius: 20px;
  padding: 0.15rem 0.6rem;
}
.badge-breaking {
  font-family: 'Archivo', sans-serif;
  font-size: 0.7rem;
  background: var(--rose);
  color: #fff;
  padding: 0.15rem 0.6rem;
  border-radius: 20px;
}
.ticket h2 { margin: 0 0 0.4rem; font-size: 1.2rem; line-height: 1.8; }
.ticket h2 a { text-decoration: none; }
.ticket h2 a:hover { color: var(--gold); }
.ticket .summary { margin: 0 0 0.5rem; color: #cbb8b1; font-size: 0.95rem; line-height: 1.9; }
.ticket-footer { font-family: 'Archivo', sans-serif; font-size: 0.72rem; color: var(--muted); }

.empty { text-align: center; color: var(--muted); padding: 3rem 1rem; font-size: 1.1rem; }
.empty span { display: block; font-family: 'Archivo', sans-serif; font-size: 0.8rem; margin-top: 0.5rem; }

footer {
  text-align: center;
  color: var(--muted);
  font-size: 0.85rem;
  padding: 2.5rem 1rem;
  border-top: 1px solid var(--hairline);
}
.footer-en { font-family: 'Archivo', sans-serif; font-size: 0.75rem; direction: ltr; }
.updated { font-family: 'Archivo', sans-serif; font-size: 0.7rem; opacity: 0.7; }

@media (max-width: 560px) {
  .ticket { flex-direction: column; }
  .ticket-image { width: 100%; height: 170px; }
  .ticket-perf { display: none; }
  .hero { min-height: 260px; margin: 1rem 0.5rem 0; }
  .hero-title { font-size: 1.35rem; }
  main { padding: 0 0.5rem 2rem; }
}
"""

if __name__ == "__main__":
    build()
