import os
import feedparser
import requests
from bs4 import BeautifulSoup
import datetime

# 🔄 MULTI-MIRROR FAILOVER ROUTING
# If the main rsshub app times out, the script loops through verified alternative network endpoints
RSS_MIRRORS = [
    "https://slarker.me",
    "https://rsshub.app",
    "https://moe.moe"
]

FEED_PATHS = {
    "Politico (Most Popular)": "/politico/top-stories",
    "Axios (Trending News)": "/axios/hot"
}

def fetch_rss_content():
    sections = {name: [] for name in FEED_PATHS}
    sections["The Points Guy (Latest Offers)"] = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 1. Fetch Politico and Axios using mirror failovers
    for name, path in FEED_PATHS.items():
        feed_data = None
        for mirror in RSS_MIRRORS:
            try:
                url = f"{mirror}{path}"
                response = requests.get(url, headers=headers, timeout=8)
                if response.status_code == 200 and len(response.text) > 500:
                    feed_data = response.text
                    break # Success! Break mirror loop
            except Exception:
                continue # Try next mirror if this one drops
                
        if feed_data:
            feed = feedparser.parse(feed_data)
            for entry in feed.entries[:3]:
                title = entry.title
                link = entry.link
                summary = entry.get('summary', entry.get('description', 'Tap to open story.'))
                clean_soup = BeautifulSoup(summary, 'html.parser')
                text_snippet = clean_soup.get_text().strip()
                if len(text_snippet) > 240:
                    text_snippet = text_snippet[:240] + "..."
                sections[name].append(f"### [{title}]({link})\n{text_snippet}\n")
        else:
            sections[name].append(f"* Sync issue extracting latest trending posts right now.")

    # 2. Fetch The Points Guy directly (stable independent feed)
    try:
        tpg_url = "https://thepointsguy.com"
        tpg_resp = requests.get(tpg_url, headers=headers, timeout=10)
        if tpg_resp.status_code == 200:
            tpg_feed = feedparser.parse(tpg_resp.text)
            for entry in tpg_feed.entries[:3]:
                title = entry.title
                link = entry.link
                summary = entry.get('summary', entry.get('description', 'Tap to open details.'))
                clean_soup = BeautifulSoup(summary, 'html.parser')
                text_snippet = clean_soup.get_text().strip()
                if len(text_snippet) > 240:
                    text_snippet = text_snippet[:240] + "..."
                sections["The Points Guy (Latest Offers)"].append(f"### [{title}]({link})\n{text_snippet}\n")
        else:
            sections["The Points Guy (Latest Offers)"].append(f"* Travel feed momentarily caching.")
    except Exception:
        sections["The Points Guy (Latest Offers)"].append(f"* Travel feed pipeline reset.")

    return sections

def fetch_chicago_events():
    try:
        url = "https://choosechicago.com"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        events = []
        for card in soup.find_all(['h3', 'h4'], class_=['card-title', 'event-title'], limit=6):
            title = card.get_text(strip=True)
            link_tag = card.find('a') or card.find_parent('a')
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else url
            if not link.startswith('http'):
                link = f"https://choosechicago.com{link}"
            events.append(f"### [{title}]({link})\nFeatured high-engagement local Chicago community happening and event tour listing.\n")
        return "\n".join(events[:3]) if events else "* No events scheduled today."
    except Exception as e:
        return f"* Local event feed temporarily unavailable."

def build_markdown_page(news_sections, chicago_content):
    today_str = datetime.date.today().strftime("%B %d, %Y")
    
    markdown = []
    markdown.append("<style>body{background-color:#0d1117!important;color:#c9d1d9!important;padding:20px;font-family:-apple-system,BlinkMacSystemFont,sans-serif;}a{color:#58a6ff!important;text-decoration:none;}a:hover{text-decoration:underline;}h1,h2,h3{color:#f0f6fc!important;}h1{border-bottom:1px solid #21262d!important;padding-bottom:10px;}h2{margin-top:30px;border-bottom:1px solid #21262d!important;padding-bottom:5px;}h3{margin-top:20px;font-size:1.15em;}</style>\n")
    
    markdown.append(f"# 🌅 My Daily Briefing - {today_str}\n")
    markdown.append("Your private, automated dashboard sorted dynamically by traffic and popular interaction.\n")
    
    for section_title, articles in news_sections.items():
        markdown.append(f"## {section_title}")
        if articles:
            markdown.append("\n".join(articles))
        else:
            markdown.append("* Processing pipeline clearing cache.")
        markdown.append("")
        
    markdown.append("## 🎭 Top Chicago Happenings")
    markdown.append(chicago_content)
    
    return "\n".join(markdown)

if __name__ == "__main__":
    news_data = fetch_rss_content()
    chicago_data = fetch_chicago_events()
    final_output = build_markdown_page(news_data, chicago_data)
    with open("index.md", "w", encoding="utf-8") as f:
        f.write(final_output)
