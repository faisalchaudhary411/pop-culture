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
import markdown as md_lib

SITE_NAME = "اردو تفریح"
SITE_NAME_EN = "Urdu Pop Culture"
SITE_URL = "https://example.com"  # TODO: replace with your real domain
SITE_TAGLINE = "فلم، ڈرامہ اور موسیقی کی تازہ ترین خبریں"
SITE_DESCRIPTION = "Latest Urdu & Pakistani entertainment news: movies, drama and music, aggregated from verified sources."
OUT_DIR = Path(__file__).parent / "docs"
FEEDS_FILE = Path(__file__).parent / "feeds.json"
ORIGINALS_DIR = Path(__file__).parent / "originals"
PAGES_DIR = Path(__file__).parent / "pages"
MAX_ITEMS_PER_CATEGORY = 40
BREAKING_HOURS = 3
TRENDING_HOURS = 8

# Each category gets its own vibrant accent + Urdu label + icon + gradient
# (used as the poster-tile fallback when an article has no image).
CATEGORY_META = {
    "Movies": {"urdu": "فلمیں", "color": "#ff2f7e", "icon": "🎬",
               "gradient": "linear-gradient(135deg,#ff2f7e,#7b2ff7)"},
    "Drama":  {"urdu": "ڈرامہ", "color": "#9b5de5", "icon": "🎭",
               "gradient": "linear-gradient(135deg,#9b5de5,#4d2a8c)"},
    "Music":  {"urdu": "موسیقی", "color": "#2de1c2", "icon": "🎵",
               "gradient": "linear-gradient(135deg,#2de1c2,#1b7d8c)"},
    "Opinion": {"urdu": "رائے", "color": "#ffc94d", "icon": "✍️",
                "gradient": "linear-gradient(135deg,#ffc94d,#ff7a3d)"},
}
DEFAULT_META = {"urdu": "خبر", "color": "#ffc94d", "icon": "★",
                "gradient": "linear-gradient(135deg,#ffc94d,#ff7a3d)"}


def load_feeds():
    with open(FEEDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_summary(raw_html, max_len=160):
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


def _first_img_from_html(raw_html):
    if not raw_html:
        return None
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_html)
    return m.group(1) if m else None


def extract_image(entry):
    """Try, in order: media:content / media:thumbnail (proper RSS media
    tags) -> first <img> inside content:encoded -> first <img> inside the
    summary/description -> enclosure links. Most WordPress-based feeds
    (common for Pakistani entertainment sites) only put the image inline
    in content:encoded, which is why the old version missed most photos."""
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key)
        if media and isinstance(media, list):
            url = media[0].get("url")
            if url:
                return url

    for content_block in entry.get("content", []) or []:
        img = _first_img_from_html(content_block.get("value", ""))
        if img:
            return img

    img = _first_img_from_html(entry.get("summary", "") or entry.get("description", ""))
    if img:
        return img

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


def hours_old(item):
    if not item["published"]:
        return 9999
    return (datetime.now(timezone.utc) - item["published"]).total_seconds() / 3600


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
    meta = CATEGORY_META.get(item["category"], DEFAULT_META)
    bg = f'style="background-image:linear-gradient(to top, rgba(15,6,20,0.97) 15%, rgba(15,6,20,0.55) 55%, rgba(15,6,20,0.15)), url(\'{item["image"]}\')"' \
        if item["image"] else f'style="background-image:{meta["gradient"]}"'
    trending = '<span class="ribbon">🔥 ٹرینڈنگ</span>' if hours_old(item) <= TRENDING_HOURS else ""
    return f"""
    <section class="hero" {bg}>
      {trending}
      <div class="hero-content">
        <span class="chip" style="--c:{meta['color']}">{meta['icon']} {meta['urdu']}</span>
        <h1 class="hero-title"><a href="{item['link']}" target="_blank" rel="noopener nofollow">{item['title']}</a></h1>
        <p class="hero-summary">{item['summary']}</p>
        <div class="hero-meta">{item['source']} · {time_ago(item['published'])}</div>
      </div>
    </section>"""


def render_tile(item):
    meta = CATEGORY_META.get(item["category"], DEFAULT_META)
    if item["image"]:
        img_style = f'style="background-image:url(\'{item["image"]}\')"'
        img_class = "tile-media"
    else:
        img_style = f'style="background-image:{meta["gradient"]}"'
        img_class = "tile-media tile-media-fallback"

    fresh = '<span class="badge-fresh">تازہ</span>' if hours_old(item) <= BREAKING_HOURS else ""
    icon_center = f'<span class="tile-icon">{meta["icon"]}</span>' if not item["image"] else ""

    return f"""
    <article class="tile">
      <a class="tile-link" href="{item['link']}" target="_blank" rel="noopener nofollow">
        <div class="{img_class}" {img_style}>
          {icon_center}
          <div class="tile-scrim">
            <span class="chip chip-sm" style="--c:{meta['color']}">{meta['icon']} {meta['urdu']}</span>
            {fresh}
            <h2 class="tile-title">{item['title']}</h2>
          </div>
        </div>
      </a>
      <div class="tile-footer">
        <span class="tile-source">{item['source']}</span>
        <span class="tile-dot">•</span>
        <span class="tile-time">{time_ago(item['published'])}</span>
      </div>
    </article>"""


NAV_ITEMS = [
    ("index.html", "سب کچھ", "All"),
    ("movies.html", "فلمیں", "Movies"),
    ("drama.html", "ڈرامہ", "Drama"),
    ("music.html", "موسیقی", "Music"),
    ("originals.html", "اوریجنلز", "Originals"),
]


def render_nav(active_file):
    tabs = []
    for fname, urdu, eng in NAV_ITEMS:
        cls = " active" if fname == active_file else ""
        tabs.append(f'<a class="tab{cls}" href="{fname}"><span class="tab-urdu">{urdu}</span><span class="tab-en">{eng}</span></a>')
    return "\n".join(tabs)


def render_ticker(headlines):
    items = "".join(
        f'<a href="{h["link"]}" target="_blank" rel="noopener nofollow">{h["title"]}</a><span class="dot">●</span>'
        for h in headlines
    )
    return f'<div class="ticker"><span class="ticker-label">تازہ ترین</span><div class="ticker-track">{items}{items}</div></div>'


FOOTER_LINKS = [
    ("about.html", "ہمارے بارے میں"),
    ("contact.html", "رابطہ"),
    ("privacy.html", "پرائیویسی پالیسی"),
    ("terms.html", "شرائط و ضوابط"),
]


def render_footer(updated):
    links = " · ".join(f'<a href="{href}">{label}</a>' for href, label in FOOTER_LINKS)
    return f"""<footer>
  <p class="footer-links">{links}</p>
  <p>مواد اصل ذرائع کے پبلک RSS فیڈز سے اکٹھا کیا گیا ہے۔</p>
  <p class="footer-en">Content aggregated from public RSS feeds of original publishers. Headlines link to source; full articles are not reproduced.</p>
  <p class="updated">Last updated: {updated}</p>
</footer>"""


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
  <h1 class="brand"><a href="index.html">{site_name}<span class="brand-en">{site_name_en}</span></a></h1>
  <p class="tagline">{tagline}</p>
  <nav class="tabs">{nav}</nav>
</header>
{ticker}
<main>
{hero}
<div class="grid">
{tiles}
</div>
</main>
{footer}
</body>
</html>"""


ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="ur" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<meta name="description" content="{page_description}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="article">
<meta property="og:title" content="{page_title}">
<meta property="og:description" content="{page_description}">
<meta property="og:url" content="{canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <h1 class="brand"><a href="index.html">{site_name}<span class="brand-en">{site_name_en}</span></a></h1>
  <p class="tagline">{tagline}</p>
  <nav class="tabs">{nav}</nav>
</header>
<main>
<article class="post">
{banner}
<div class="post-body prose">
{meta}
<h1>{title}</h1>
{content}
</div>
</article>
</main>
{footer}
</body>
</html>"""


def parse_frontmatter(text):
    """Very small frontmatter parser: everything between the first two `---`
    lines is treated as simple `key: value` pairs (split on the FIRST colon
    only, so values containing URLs with colons still work); everything
    after the second `---` is the markdown body."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    front_raw, body = m.groups()
    meta = {}
    for line in front_raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, body


def render_original_tile(post):
    meta = CATEGORY_META.get(post["category"], CATEGORY_META["Opinion"])
    if post["image"]:
        img_style = f'style="background-image:url(\'{post["image"]}\')"'
        img_class = "tile-media"
    else:
        img_style = f'style="background-image:{meta["gradient"]}"'
        img_class = "tile-media tile-media-fallback"
    icon_center = f'<span class="tile-icon">{meta["icon"]}</span>' if not post["image"] else ""
    date_str = post["date"].strftime("%d %b %Y") if post["date"] else ""
    return f"""
    <article class="tile">
      <a class="tile-link" href="{post['slug']}.html">
        <div class="{img_class}" {img_style}>
          {icon_center}
          <div class="tile-scrim">
            <span class="chip chip-sm" style="--c:{meta['color']}">{meta['icon']} {meta['urdu']}</span>
            <span class="badge-original">اوریجنل</span>
            <h2 class="tile-title">{post['title']}</h2>
          </div>
        </div>
      </a>
      <div class="tile-footer">
        <span class="tile-source">اردو تفریح</span>
        <span class="tile-dot">•</span>
        <span class="tile-time">{date_str}</span>
      </div>
    </article>"""


def build_originals(nav_html, ticker_html, updated):
    """Reads originals/*.md, writes one .html per post plus originals.html
    (an index of all posts using the same tile design as the RSS grid)."""
    posts = []
    if ORIGINALS_DIR.exists():
        for md_path in sorted(ORIGINALS_DIR.glob("*.md")):
            raw = md_path.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(raw)
            date_obj = None
            if fm.get("date"):
                try:
                    date_obj = datetime.strptime(fm["date"].strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
            posts.append({
                "slug": md_path.stem,
                "title": fm.get("title", md_path.stem),
                "category": fm.get("category", "Opinion").strip(),
                "excerpt": fm.get("excerpt", ""),
                "image": fm.get("image", "").strip() or None,
                "date": date_obj,
                "body_html": md_lib.markdown(body.strip(), extensions=["extra"]),
            })
    posts.sort(key=lambda p: p["date"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    # Individual post pages
    for post in posts:
        meta = CATEGORY_META.get(post["category"], CATEGORY_META["Opinion"])
        banner = ""
        if post["image"]:
            banner = f'<div class="post-banner" style="background-image:url(\'{post["image"]}\')"></div>'
        date_str = post["date"].strftime("%d %b %Y") if post["date"] else ""
        meta_line = f'<div class="post-meta"><span class="chip chip-sm" style="--c:{meta["color"]}">{meta["icon"]} {meta["urdu"]}</span> <span class="badge-original">اوریجنل</span> <span class="post-date">{date_str}</span></div>'
        page = ARTICLE_TEMPLATE.format(
            page_title=f"{post['title']} — {SITE_NAME}",
            page_description=post["excerpt"] or SITE_DESCRIPTION,
            canonical=f"{SITE_URL}/{post['slug']}.html",
            site_name=SITE_NAME,
            site_name_en=SITE_NAME_EN,
            tagline=SITE_TAGLINE,
            nav=nav_html,
            banner=banner,
            meta=meta_line,
            title=post["title"],
            content=post["body_html"],
            footer=render_footer(updated),
        )
        (OUT_DIR / f"{post['slug']}.html").write_text(page, encoding="utf-8")
        print(f"  wrote {post['slug']}.html (original post)")

    # Originals index
    tiles_html = "\n".join(render_original_tile(p) for p in posts) or \
        '<p class="empty">ابھی تک کوئی اوریجنل تحریر شائع نہیں ہوئی۔</p>'
    page = PAGE_TEMPLATE.format(
        page_title=f"اوریجنلز — {SITE_NAME} | {SITE_NAME_EN}",
        page_description=f"Original writing and opinion pieces: {SITE_DESCRIPTION}",
        canonical=f"{SITE_URL}/originals.html",
        site_name=SITE_NAME,
        site_name_en=SITE_NAME_EN,
        tagline=SITE_TAGLINE,
        nav=nav_html,
        ticker="",
        hero="",
        tiles=tiles_html,
        footer=render_footer(updated),
    )
    (OUT_DIR / "originals.html").write_text(page, encoding="utf-8")
    print(f"  wrote originals.html ({len(posts)} posts)")


def build_pages(nav_html, updated):
    """Reads pages/*.md (about, contact, privacy, terms) and writes matching
    .html files — simple prose pages, no category/image/date chrome."""
    if not PAGES_DIR.exists():
        return
    for md_path in sorted(PAGES_DIR.glob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(raw)
        title = fm.get("title", md_path.stem)
        body_html = md_lib.markdown(body.strip(), extensions=["extra"])
        slug = md_path.stem
        page = ARTICLE_TEMPLATE.format(
            page_title=f"{title} — {SITE_NAME}",
            page_description=SITE_DESCRIPTION,
            canonical=f"{SITE_URL}/{slug}.html",
            site_name=SITE_NAME,
            site_name_en=SITE_NAME_EN,
            tagline=SITE_TAGLINE,
            nav=nav_html,
            banner="",
            meta="",
            title=title,
            content=body_html,
            footer=render_footer(updated),
        )
        (OUT_DIR / f"{slug}.html").write_text(page, encoding="utf-8")
        print(f"  wrote {slug}.html (static page)")


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

        tiles_html = "\n".join(render_tile(it) for it in rest) or \
            ('' if items else '<p class="empty">فی الحال کوئی خبر دستیاب نہیں<br><span>Feeds temporarily unavailable — check back shortly.</span></p>')

        page = PAGE_TEMPLATE.format(
            page_title=f"{CATEGORY_META.get(category, DEFAULT_META)['urdu']} — {SITE_NAME} | {SITE_NAME_EN}" if category != "All" else f"{SITE_NAME} | {SITE_NAME_EN}",
            page_description=f"Latest {category} news: {SITE_DESCRIPTION}" if category != "All" else SITE_DESCRIPTION,
            canonical=f"{SITE_URL}/{fname}",
            site_name=SITE_NAME,
            site_name_en=SITE_NAME_EN,
            tagline=SITE_TAGLINE,
            nav=render_nav(fname),
            ticker=ticker_html,
            hero=hero_html,
            tiles=tiles_html,
            footer=render_footer(updated),
        )
        (OUT_DIR / fname).write_text(page, encoding="utf-8")
        print(f"  wrote {fname} ({len(items)} items)")

    print("Originals:")
    build_originals(render_nav("originals.html"), "", updated)

    print("Static pages:")
    build_pages(render_nav(""), updated)

    all_filenames = list(pages.keys()) + ["originals.html"]
    if PAGES_DIR.exists():
        all_filenames += [f"{p.stem}.html" for p in PAGES_DIR.glob("*.md")]
    if ORIGINALS_DIR.exists():
        all_filenames += [f"{p.stem}.html" for p in ORIGINALS_DIR.glob("*.md")]

    write_static_assets()
    write_sitemap(all_filenames)
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
@import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&family=Archivo+Black&family=Archivo:wght@400;600;700&display=swap');

:root {
  --bg: #14091f;
  --surface: #1f1130;
  --surface-raised: #291640;
  --pink: #ff2f7e;
  --violet: #9b5de5;
  --teal: #2de1c2;
  --gold: #ffc94d;
  --text: #f5f0ff;
  --muted: #b8a8cc;
  --hairline: #3a2456;
}

* { box-sizing: border-box; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }

body {
  margin: 0;
  background: var(--bg);
  background-image: radial-gradient(circle at 20% 0%, rgba(255,47,126,0.12), transparent 40%),
                     radial-gradient(circle at 80% 10%, rgba(45,225,194,0.10), transparent 40%);
  color: var(--text);
  font-family: 'Noto Nastaliq Urdu', serif;
}
a { color: inherit; }
a:focus-visible, button:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }

/* ---------- Header ---------- */
.site-header { text-align: center; padding: 2.2rem 1rem 0; }
.brand a { text-decoration: none; }
.brand {
  font-size: 2.4rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(90deg, var(--pink), var(--violet));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.brand-en {
  display: block;
  font-family: 'Archivo Black', sans-serif;
  font-size: 0.62rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: var(--muted);
  margin-top: 0.35rem;
  -webkit-text-fill-color: var(--muted);
}
.tagline { font-size: 0.95rem; color: var(--muted); margin: 0.7rem 0 0; }

.tabs {
  display: flex;
  justify-content: center;
  gap: 0.6rem;
  margin: 1.5rem auto 0;
  padding: 0 1rem;
  flex-wrap: wrap;
  max-width: 600px;
}
.tab {
  font-family: 'Archivo', sans-serif;
  text-decoration: none;
  color: var(--muted);
  padding: 0.5rem 1.1rem;
  border-radius: 30px;
  border: 1px solid var(--hairline);
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
}
.tab-urdu { font-family: 'Noto Nastaliq Urdu', serif; font-size: 1.05rem; }
.tab-en { font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.8; }
.tab.active {
  background: linear-gradient(90deg, var(--pink), var(--violet));
  color: #fff;
  border-color: transparent;
}
.tab:hover:not(.active) { border-color: var(--pink); color: var(--text); }

/* ---------- Ticker ---------- */
.ticker {
  margin-top: 1.5rem;
  background: var(--surface);
  border-top: 1px solid var(--hairline);
  border-bottom: 1px solid var(--hairline);
  display: flex;
  align-items: center;
  overflow: hidden;
  white-space: nowrap;
}
.ticker-label {
  flex-shrink: 0;
  font-family: 'Archivo Black', sans-serif;
  font-size: 0.68rem;
  letter-spacing: 0.05em;
  background: var(--gold);
  color: #251200;
  padding: 0.5rem 0.9rem;
  animation: pulse-glow 1.8s ease-in-out infinite;
}
@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255,201,77,0.6); }
  50% { box-shadow: 0 0 0 6px rgba(255,201,77,0); }
}
.ticker-track {
  display: inline-block;
  padding: 0.55rem 0;
  animation: scroll-rtl 40s linear infinite;
  font-family: 'Archivo', sans-serif;
  font-size: 0.82rem;
}
.ticker-track a { text-decoration: none; color: var(--text); margin-inline-end: 0.7rem; }
.ticker-track a:hover { color: var(--pink); }
.ticker .dot { color: var(--pink); margin-inline-end: 0.7rem; font-size: 0.5rem; vertical-align: middle; }
@keyframes scroll-rtl { from { transform: translateX(0); } to { transform: translateX(50%); } }

/* ---------- Chips ---------- */
.chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-family: 'Archivo', sans-serif;
  font-weight: 700;
  font-size: 0.72rem;
  background: var(--c, var(--pink));
  color: #1a0a10;
  padding: 0.25rem 0.7rem;
  border-radius: 20px;
}
.chip-sm { font-size: 0.68rem; padding: 0.2rem 0.6rem; }

/* ---------- Hero ---------- */
main { max-width: 1080px; margin: 0 auto; padding: 0 1rem 2rem; }
.hero {
  position: relative;
  min-height: 380px;
  border-radius: 18px;
  margin-top: 1.5rem;
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: flex-end;
  overflow: hidden;
}
.ribbon {
  position: absolute;
  top: 1.1rem; inset-inline-start: 1.1rem;
  font-family: 'Archivo Black', sans-serif;
  font-size: 0.72rem;
  background: var(--gold);
  color: #2a1400;
  padding: 0.35rem 0.9rem;
  border-radius: 20px;
}
.hero-content { padding: 2rem 1.6rem 1.7rem; width: 100%; }
.hero-title { margin: 0.7rem 0 0.6rem; font-size: 1.9rem; line-height: 1.75; }
.hero-title a { text-decoration: none; }
.hero-title a:hover { color: var(--gold); }
.hero-summary { color: #e6d9f7; font-size: 1.05rem; line-height: 1.9; max-width: 65ch; margin: 0 0 0.7rem; }
.hero-meta { font-family: 'Archivo', sans-serif; font-size: 0.78rem; color: var(--muted); }

/* ---------- Poster grid ---------- */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1.1rem;
  margin-top: 1.6rem;
}
.tile {
  background: var(--surface);
  border: 1px solid var(--hairline);
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.tile-link { text-decoration: none; color: inherit; }
.tile-media {
  aspect-ratio: 4 / 3;
  background-size: cover;
  background-position: center;
  position: relative;
  display: flex;
  align-items: flex-end;
}
.tile-media-fallback { display: flex; align-items: center; justify-content: center; }
.tile-icon { position: absolute; top: 50%; inset-inline-start: 50%; transform: translate(-50%,-50%); font-size: 2.6rem; opacity: 0.9; }
.tile-scrim {
  position: relative;
  width: 100%;
  padding: 2.5rem 0.9rem 0.8rem;
  background: linear-gradient(to top, rgba(10,4,16,0.95) 25%, rgba(10,4,16,0.55) 65%, transparent);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.badge-fresh {
  align-self: flex-start;
  font-family: 'Archivo Black', sans-serif;
  font-size: 0.62rem;
  background: var(--pink);
  color: #fff;
  padding: 0.15rem 0.55rem;
  border-radius: 20px;
}
.tile-title {
  margin: 0.1rem 0 0;
  font-size: 1.05rem;
  line-height: 1.7;
  color: #fff;
  text-shadow: 0 2px 8px rgba(0,0,0,0.6);
}
.tile-link:hover .tile-title { color: var(--gold); }
.tile-footer {
  padding: 0.55rem 0.9rem;
  font-family: 'Archivo', sans-serif;
  font-size: 0.72rem;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.tile-dot { color: var(--pink); font-size: 0.5rem; }

.empty { text-align: center; color: var(--muted); padding: 3rem 1rem; font-size: 1.1rem; grid-column: 1/-1; }
.empty span { display: block; font-family: 'Archivo', sans-serif; font-size: 0.8rem; margin-top: 0.5rem; }

footer { text-align: center; color: var(--muted); font-size: 0.85rem; padding: 2.5rem 1rem; border-top: 1px solid var(--hairline); margin-top: 1rem; }
.footer-links {
  font-family: 'Archivo', sans-serif;
  font-size: 0.8rem;
  margin-bottom: 1rem;
}
.footer-links a { text-decoration: none; color: var(--text); margin: 0 0.4rem; }
.footer-links a:hover { color: var(--pink); }
.badge-original {
  display: inline-block;
  font-family: 'Archivo Black', sans-serif;
  font-size: 0.6rem;
  background: var(--gold);
  color: #2a1400;
  padding: 0.15rem 0.55rem;
  border-radius: 20px;
}

/* ---------- Article / static pages ---------- */
.post { max-width: 760px; margin: 1.5rem auto 0; padding: 0 1rem; }
.post-banner {
  aspect-ratio: 16/9;
  background-size: cover;
  background-position: center;
  border-radius: 14px;
  margin-bottom: 1.5rem;
}
.post-meta { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.8rem; font-family: 'Archivo', sans-serif; }
.post-date { font-size: 0.78rem; color: var(--muted); }
.prose h1 { font-size: 1.9rem; line-height: 1.8; margin: 0 0 1.2rem; }
.prose h2 { font-size: 1.4rem; line-height: 1.8; margin: 1.8rem 0 0.8rem; color: var(--gold); }
.prose h3 { font-size: 1.15rem; margin: 1.4rem 0 0.6rem; }
.prose p { line-height: 2.1; font-size: 1.05rem; color: #e6d9f7; margin: 0 0 1.1rem; }
.prose ul, .prose ol { line-height: 2.1; font-size: 1.05rem; color: #e6d9f7; padding-inline-start: 1.5rem; margin: 0 0 1.1rem; }
.prose a { color: var(--pink); }
.prose img { max-width: 100%; border-radius: 10px; margin: 1rem 0; }
.prose blockquote {
  border-inline-start: 3px solid var(--violet);
  margin: 1.2rem 0;
  padding: 0.3rem 1.2rem;
  color: var(--muted);
}
.prose code { background: var(--surface); padding: 0.15rem 0.4rem; border-radius: 4px; font-family: monospace; direction: ltr; display: inline-block; }
.footer-en { font-family: 'Archivo', sans-serif; font-size: 0.75rem; direction: ltr; }
.updated { font-family: 'Archivo', sans-serif; font-size: 0.7rem; opacity: 0.7; }

@media (max-width: 560px) {
  .brand { font-size: 1.9rem; }
  .hero { min-height: 300px; }
  .hero-title { font-size: 1.4rem; }
  .grid { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.8rem; }
  .tile-title { font-size: 0.95rem; }
}
"""

if __name__ == "__main__":
    build()
