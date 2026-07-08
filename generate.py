"""
Static site generator for the Urdu Pop Culture aggregator.

Run this script (locally is not required — GitHub Actions runs it on a
schedule) and it writes plain .html files into docs/. Those files are
served as-is by GitHub Pages: no JS framework, no client-side rendering,
so Google sees full content immediately and pages load instantly.

Edit feeds.json to add/remove sources. Do not edit docs/ by hand — it is
regenerated every run and your edits would be overwritten.
"""
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import feedparser

SITE_NAME = "اردو تفریح | Urdu Pop Culture"
SITE_URL = "https://example.com"  # TODO: replace with your real domain
SITE_TAGLINE = "Movies, Drama &amp; Music news from verified Urdu and Pakistani sources"
OUT_DIR = Path(__file__).parent / "docs"
FEEDS_FILE = Path(__file__).parent / "feeds.json"
MAX_ITEMS_PER_CATEGORY = 40


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_summary(raw_html, max_len=220):
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


def fetch_feed(name, url):
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
            })
    except Exception as ex:
        print(f"  ! failed to fetch {name} ({url}): {ex}")
    return items


def fetch_category(feeds_dict):
    all_items = []
    for name, url in feeds_dict.items():
        print(f"  fetching {name}...")
        all_items.extend(fetch_feed(name, url))
    all_items.sort(
        key=lambda x: x["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return all_items


def render_card(item):
    img_tag = ""
    if item["image"]:
        img_tag = f'<img src="{item["image"]}" alt="" loading="lazy" width="160" height="110">'
    date_str = ""
    time_tag = ""
    if item["published"]:
        date_str = item["published"].strftime("%d %b %Y")
        time_tag = f'<time datetime="{item["published"].isoformat()}">{date_str}</time>'
    return f"""
    <article class="card">
      {img_tag}
      <div class="card-body">
        <div class="card-meta">{item['source']} {('· ' + date_str) if date_str else ''}</div>
        <h2><a href="{item['link']}" target="_blank" rel="noopener nofollow">{item['title']}</a></h2>
        <p class="summary">{item['summary']}</p>
      </div>
    </article>"""


NAV_ITEMS = [
    ("index.html", "سب کچھ", "All"),
    ("movies.html", "فلمیں", "Movies"),
    ("drama.html", "ڈرامہ", "Drama"),
    ("music.html", "موسیقی", "Music"),
]


def render_nav(active_file):
    links = []
    for fname, urdu, eng in NAV_ITEMS:
        cls = ' class="active"' if fname == active_file else ""
        links.append(f'<a href="{fname}"{cls}>{urdu} <span>({eng})</span></a>')
    return "\n".join(links)


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
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <h1><a href="index.html">{site_name}</a></h1>
  <p>{tagline}</p>
  <nav>{nav}</nav>
</header>
<main>
{cards}
</main>
<footer>
  <p>Content is aggregated from public RSS feeds of the original publishers.
  Headlines link back to the source; full articles are not reproduced here.</p>
  <p>Last updated: {updated}</p>
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
        category_items[category] = fetch_category(feed_dict)

    # All page: merge everything, newest first
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
        cards_html = "\n".join(render_card(it) for it in items) or \
            '<p class="empty">فی الحال کوئی خبر دستیاب نہیں (feeds temporarily unavailable)</p>'
        page = PAGE_TEMPLATE.format(
            page_title=f"{category} — {SITE_NAME}" if category != "All" else SITE_NAME,
            page_description=f"Latest {category} news: {SITE_TAGLINE}",
            canonical=f"{SITE_URL}/{fname}",
            site_name=SITE_NAME,
            tagline=SITE_TAGLINE,
            nav=render_nav(fname),
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
    urls = "\n".join(
        f"  <url><loc>{SITE_URL}/{f}</loc></url>" for f in filenames
    )
    sitemap = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>'
    (OUT_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Noto Nastaliq Urdu', serif;
  background: #0f0f0f;
  color: #eaeaea;
}
a { color: inherit; }

.site-header {
  text-align: center;
  padding: 1.5rem 1rem 1rem;
  border-bottom: 2px solid #ff4545;
}
.site-header h1 a { color: #ff4545; text-decoration: none; font-size: 1.8rem; }
.site-header p { color: #999; font-size: 0.85rem; margin: 0.3rem 0 1rem; }
.site-header nav { display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap; }
.site-header nav a {
  text-decoration: none;
  color: #ccc;
  padding: 0.3rem 0.8rem;
  border-radius: 20px;
  border: 1px solid #333;
  font-size: 0.95rem;
}
.site-header nav a.active, .site-header nav a:hover { background: #ff4545; color: #fff; border-color: #ff4545; }
.site-header nav a span { font-family: sans-serif; font-size: 0.75rem; opacity: 0.7; }

main {
  max-width: 900px;
  margin: 1.5rem auto;
  padding: 0 1rem;
  display: grid;
  gap: 1rem;
}

.card {
  display: flex;
  gap: 1rem;
  background: #1a1a1a;
  border: 1px solid #2a2a2a;
  border-radius: 10px;
  padding: 1rem;
}
.card img { width: 140px; height: 100px; object-fit: cover; border-radius: 8px; flex-shrink: 0; }
.card-body { flex: 1; }
.card-meta { font-size: 0.75rem; color: #888; margin-bottom: 0.3rem; font-family: sans-serif; }
.card h2 { margin: 0 0 0.4rem; font-size: 1.15rem; line-height: 1.7; }
.card h2 a { text-decoration: none; }
.card h2 a:hover { color: #ff4545; }
.card .summary { margin: 0; color: #bbb; font-size: 0.95rem; line-height: 1.9; }
.empty { text-align: center; color: #888; padding: 2rem; }

footer {
  text-align: center;
  color: #666;
  font-size: 0.8rem;
  font-family: sans-serif;
  padding: 2rem 1rem;
  border-top: 1px solid #222;
}

@media (max-width: 500px) {
  .card { flex-direction: column; }
  .card img { width: 100%; height: 160px; }
}
"""

if __name__ == "__main__":
    build()
