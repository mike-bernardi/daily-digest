import os
import feedparser
import requests
from bs4 import BeautifulSoup
import datetime

RSS_FEEDS = {
    "Politico": "https://politico.com",
    "Axios": "https://axios.com",
    "The Points Guy": "https://thepointsguy.com"
}

def fetch_rss_content():
    sections = {name: [] for name in RSS_FEEDS}
    
    # Adding desktop headers to bypass crawler firewalls on Axios and TPG
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
    }
    
    for source_name, url in RSS_FEEDS.items():
        try:
            # We fetch the raw text via requests using headers first, then pass it to feedparser
            response = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(response.text)
            
            for entry in feed.entries[:3]:
                title = entry.title
                link = entry.link
                summary = entry.get('summary', entry.get('description', 'Tap to read full coverage.'))
                
                clean_soup = BeautifulSoup(summary, 'html.parser')
                text_snippet = clean_soup.get_text()
                if len(text_snippet) > 160:
                    text_snippet = text_snippet[:160] + "..."
                
                sections[source_name].append(f"* **[{title}]({link})** — {text_snippet}")
        except Exception as e:
            sections[source_name].append(f"* Failed to pull {source_name} feed data.")
            
    return sections

def fetch_chicago_events():
    try:
        url = "https://choosechicago.com"
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)"}
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
        return "\n".join(events) if events else "* No events found for today."
    except Exception as e:
        return f"* Could not pull Chicago events dynamically right now."

def build_markdown_page(news_sections, chicago_content):
    today_str = datetime.date.today().strftime("%B %d, %Y")
    
    markdown = []
    markdown.append(f"# 🌅 My Daily Briefing - {today_str}\n")
    markdown.append("Welcome back! Here is your private, automated dashboard updated live on your device.\n")
    
    markdown.append("## 🏛️ National News (Politico & Axios)")
    if news_sections.get("Politico") or news_sections.get("Axios"):
        markdown.append("\n".join(news_sections.get("Politico", [])))
        markdown.append("\n".join(news_sections.get("Axios", [])))
    else:
        markdown.append("* No national headlines found.")
    markdown.append("")
    
    markdown.append("## ✈️ Points, Miles & Travel (The Points Guy)")
    if news_sections.get("The Points Guy"):
        markdown.append("\n".join(news_sections.get("The Points Guy", [])))
    else:
        markdown.append("* No travel headlines found.")
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
