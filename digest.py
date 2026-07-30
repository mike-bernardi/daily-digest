import os
import re
import json
import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import datetime

# ------------------------------------------------------------------
# CACHE FILE — lets the page fall back to last-good content instead
# of showing "sync issue" placeholders when a source hiccups.
# Make sure your workflow commits this file back to the repo after
# each run, or the fallback has nothing to fall back to.
# ------------------------------------------------------------------
CACHE_PATH = "cache.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/rss+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

POLITICO_TRENDING_FEED = "https://rss.politico.com/politicopicks.xml"
AXIOS_HOMEPAGE = "https://www.axios.com/"
AXIOS_FALLBACK_FEED = "https://www.axios.com/feeds/feed.rss"  # chronological, not trending — last resort only
TPG_FEED = "https://thepointsguy.com/feed/"


def make_session():
    """Session with retry/backoff so a single dropped connection
    doesn't immediately fall through to the cache."""
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(cache):
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except OSError:
        pass


def clean_snippet(raw_html, max_len=240):
    text = BeautifulSoup(raw_html, "html.parser").get_text().strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def use_cache_or_fail(cache, key, label):
    cached = cache.get(key)
    if cached and cached.get("articles"):
        stale_note = f"*(showing last successful update: {cached['updated'][:10]})*\n"
        return [stale_note] + cached["articles"]
    return [f"* Unable to load {label} right now — no cached copy available."]


def store_cache(cache, key, articles):
    cache[key] = {"articles": articles, "updated": datetime.datetime.now().isoformat()}


# ------------------------------------------------------------------
# POLITICO — rss.politico.com/politicopicks.xml is Politico's own
# "top stories" / most-read feed (the same one Facebook's old
# Trending module pulled from). This is a genuine trending endpoint,
# not a general chronological feed, so no scraping needed here.
# ------------------------------------------------------------------
def fetch_politico_trending(session, cache):
    key = "politico"
    try:
        resp = session.get(POLITICO_TRENDING_FEED, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            raise ValueError("Politico Picks feed returned no entries")

        articles = []
        for entry in feed.entries[:3]:
            title = entry.get("title", "Untitled")
            link = entry.get("link", POLITICO_TRENDING_FEED)
            summary = entry.get("summary", entry.get("description", "Tap to open story."))
            articles.append(f"### [{title}]({link})\n{clean_snippet(summary)}\n")

        store_cache(cache, key, articles)
        return articles
    except Exception as e:
        print(f"[warn] Politico trending fetch failed: {e}")
        return use_cache_or_fail(cache, key, "Politico trending stories")


# ------------------------------------------------------------------
# AXIOS — no official "trending" RSS feed exists. Their homepage has
# a real "MOST POPULAR" module that's server-rendered (confirmed —
# it comes back in a plain HTTP GET, no headless browser needed), so
# we scrape it directly the same way the Chicago section works.
#
# NOTE: this locates the module by its visible "MOST POPULAR" text
# rather than a CSS class, since class names on Next.js sites are
# often hashed/unstable — matching on stable text + Axios's URL date
# pattern (/YYYY/MM/DD/slug) is more resilient to markup changes.
# If Axios redesigns the homepage, this is the piece to revisit.
# ------------------------------------------------------------------
AXIOS_ARTICLE_URL_RE = re.compile(r"^https://www\.axios\.com/\d{4}/\d{2}/\d{2}/[a-z0-9\-]+/?$")


def fetch_axios_trending(session, cache):
    key = "axios"
    try:
        resp = session.get(AXIOS_HOMEPAGE, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        marker = soup.find(string=lambda s: s and "most popular" in s.lower())
        if not marker:
            raise ValueError('"MOST POPULAR" module not found on Axios homepage')

        # Walk up a few levels to a container broad enough to hold the
        # whole module, then pull article links out of it in order.
        container = marker.find_parent()
        for _ in range(4):
            if container and container.find_all("a", href=True):
                break
            container = container.find_parent() if container else None
        if not container:
            raise ValueError("Could not locate Most Popular container")

        seen = set()
        articles = []
        for a in container.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                href = f"https://www.axios.com{href}"
            if not AXIOS_ARTICLE_URL_RE.match(href):
                continue
            title = a.get_text(strip=True)
            if not title or href in seen:
                continue
            seen.add(href)
            articles.append(f"### [{title}]({href})\nFrom Axios' Most Popular list.\n")
            if len(articles) == 3:
                break

        if not articles:
            raise ValueError("No article links found in Most Popular module")

        store_cache(cache, key, articles)
        return articles

    except Exception as e:
        print(f"[warn] Axios trending scrape failed: {e}")
        # Try the plain chronological feed as a last resort before cache —
        # it's not "trending" but it's better than nothing.
        try:
            resp = session.get(AXIOS_FALLBACK_FEED, headers=HEADERS, timeout=12)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            if feed.entries:
                articles = []
                for entry in feed.entries[:3]:
                    title = entry.get("title", "Untitled")
                    link = entry.get("link", AXIOS_FALLBACK_FEED)
                    summary = entry.get("summary", entry.get("description", "Tap to open story."))
                    articles.append(f"### [{title}]({link})\n{clean_snippet(summary)}\n")
                note = "*(Most Popular module unavailable — showing latest stories instead)*\n"
                return [note] + articles
        except Exception as e2:
            print(f"[warn] Axios fallback feed also failed: {e2}")

        return use_cache_or_fail(cache, key, "Axios trending stories")


# ------------------------------------------------------------------
# THE POINTS GUY — no trending endpoint, but "Latest Offers" maps
# to their Deals vertical. Rather than scrape /deals (fragile), we
# use TPG's real feed and filter for posts whose URL falls under
# /deals/ — the feed already contains deals posts, so this is just
# a filter, not a scrape.
# ------------------------------------------------------------------
def fetch_tpg_deals(session, cache):
    key = "tpg"
    try:
        resp = session.get(TPG_FEED, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        if not feed.entries:
            raise ValueError("TPG feed returned no entries")

        deals_entries = [e for e in feed.entries if "/deals/" in e.get("link", "")]
        chosen = (deals_entries or feed.entries)[:3]

        articles = []
        for entry in chosen:
            title = entry.get("title", "Untitled")
            link = entry.get("link", TPG_FEED)
            summary = entry.get("summary", entry.get("description", "Tap to open details."))
            articles.append(f"### [{title}]({link})\n{clean_snippet(summary)}\n")

        if not deals_entries:
            articles.insert(0, "*(No dedicated deals posts in the current feed — showing latest TPG stories)*\n")

        store_cache(cache, key, articles)
        return articles
    except Exception as e:
        print(f"[warn] TPG deals fetch failed: {e}")
        return use_cache_or_fail(cache, key, "The Points Guy deals")


def fetch_chicago_events(session, cache):
    key = "chicago"
    try:
        url = "https://choosechicago.com"
        resp = session.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        events = []
        for card in soup.find_all(["h3", "h4"], class_=["card-title", "event-title"], limit=6):
            title = card.get_text(strip=True)
            link_tag = card.find("a") or card.find_parent("a")
            link = link_tag["href"] if link_tag and link_tag.has_attr("href") else url
            if not link.startswith("http"):
                link = f"https://choosechicago.com{link}"
            events.append(f"### [{title}]({link})\nFeatured Chicago community event.\n")

        if not events:
            raise ValueError("No event cards found (site markup may have changed)")

        result = events[:3]
        store_cache(cache, key, result)
        return "\n".join(result)

    except Exception as e:
        print(f"[warn] Chicago events fetch failed: {e}")
        fallback = use_cache_or_fail(cache, key, "Chicago events")
        return "\n".join(fallback) if isinstance(fallback, list) else fallback


def build_markdown_page(news_sections, chicago_content):
    today_str = datetime.date.today().strftime("%B %d, %Y")

    markdown = []
    markdown.append(
        "<style>body{background-color:#0d1117!important;color:#c9d1d9!important;"
        "padding:20px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;}"
        "a{color:#58a6ff!important;text-decoration:none;}a:hover{text-decoration:underline;}"
        "h1,h2,h3{color:#f0f6fc!important;}h1{border-bottom:1px solid #21262d!important;"
        "padding-bottom:10px;}h2{margin-top:30px;border-bottom:1px solid #21262d!important;"
        "padding-bottom:5px;}h3{margin-top:20px;font-size:1.15em;}</style>\n"
    )

    markdown.append(f"# \U0001F305 My Daily Briefing - {today_str}\n")
    markdown.append("Your private, automated dashboard sorted dynamically by traffic and popular interaction.\n")

    for section_title, articles in news_sections.items():
        markdown.append(f"## {section_title}")
        markdown.append("\n".join(articles) if articles else "* No content available.")
        markdown.append("")

    markdown.append("## \U0001F3AD Top Chicago Happenings")
    markdown.append(chicago_content)

    return "\n".join(markdown)


if __name__ == "__main__":
    cache = load_cache()
    session = make_session()

    news_data = {
        "Politico (Most Popular)": fetch_politico_trending(session, cache),
        "Axios (Trending News)": fetch_axios_trending(session, cache),
        "The Points Guy (Latest Offers)": fetch_tpg_deals(session, cache),
    }
    chicago_data = fetch_chicago_events(session, cache)

    save_cache(cache)

    final_output = build_markdown_page(news_data, chicago_data)

    with open("index.md", "w", encoding="utf-8") as f:
        f.write(final_output)

    print("Briefing built successfully.")
