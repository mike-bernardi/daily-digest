import os
import feedparser
import requests
from bs4 import BeautifulSoup
import datetime

# Swapped Axios to their active public RSS feed endpoint
RSS_FEEDS = {
    "Politico": "https://politico.com",
    "Axios": "https://axios.com",
    "The Points Guy": "https://thepointsguy.com"
}

def fetch_rss_content():
    sections = {name: [] for name in RSS_FEEDS}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    for source_name, url in RSS_FEEDS.items():
        try:
            response = requests.get(url, headers=headers, timeout=12)
            # Check if feed contents are returning text data safely
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                items = feed.entries[:3] if feed.entries else []
                
                for entry in items:
                    title = entry.title
                    link = entry.link
                    summary = entry.get('summary', entry.get('description', 'Tap link to open full story.'))
                    
                    clean_soup = BeautifulSoup(summary, 'html.parser')
                    text_snippet = clean_soup.get_text().strip()
                    if len(text_snippet) > 150:
                        text_snippet = text_snippet[:150] + "..."
                    
                    sections[source_name].append(f"* **[{title}]({link})** — {text_snippet}")
            else:
                sections[source_name].append(f"* Connection hold ({response.status_code}) fetching current updates.")
        except Exception as e:
            sections[source_name].append(f"* Feed momentarily offline.")
            
    return sections

def fetch_chicago_events():
    try:
        url = "https://choosechicago.com"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        events = []
        for card in soup.find_all(['h3', 'h4'], class_=['card-title', 'event-title'], limit=4):
            title = card.get_text(strip=True)
            link_tag = card.find('a') or card.find_parent('a')
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else url
            if not link.startswith('http'):
                link = f"https://choosechicago.com{link}"
            events.append(f"* **[{title}]({link})** — Featured local Chicago community happening and event tour.")
        return "\n".join(events) if events else "* No events scheduled today."
    except Exception as e:
        return f"* Local event feed temporarily unavailable."

def build_markdown_page(news_sections, chicago_content):
    today_str = datetime.date.today().strftime("%B %d, %Y")
    
    markdown = []
    # Injecting clean CSS variables at the absolute top to force phone screen to render dark mode
    markdown.append("<style>body{background-color:#0d1117!important;color:#c9d1d9!important;padding:20px;}a{color:#58a6ff!important;}h1,h2,h3{color:#f0f6fc!important;border-bottom:1px solid #21262d!important;}</style>\n")
    
    markdown.append(f"# 🌅 My Daily Briefing - {today_str}\n")
    markdown.append("Your private, automated dashboard updated live on your device.\n")
    
    markdown.append("## 🏛️ National News (Politico & Axios)")
    pol_articles = news_sections.get("Politico", [])
    ax_articles = news_sections.get("Axios", [])
    if pol_articles or ax_articles:
        markdown.append("\n".join(pol_articles + ax_articles))
    else:
        markdown.append("* Waiting on national pipeline processing.")
    markdown.append("")
    
    markdown.append("## ✈️ Points, Miles & Travel (The Points Guy)")
    tpg_articles = news_sections.get("The Points Guy", [])
    if tpg_articles:
        markdown.append("\n".join(tpg_articles))
    else:
        markdown.append("* Waiting on travel pipeline processing.")
    markdown.append("")
    
    markdown.append("## 🎭 What to Do in Chicago")
    markdown.append(chicago_content)
    
    return "\n".join(markdown)

if __name__ == "__main__":
    news_data = fetch_rss_content()
    chicago_data = fetch_chicago_events()
    final_output = build_markdown_page(news_data, chicago_data)
    with open("index.md", "w", encoding="utf-8") as f:
        f.write(final_output)
