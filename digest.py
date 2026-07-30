import os
import feedparser
import requests
from bs4 import BeautifulSoup
import datetime

# 📈 UPDATED ENDPOINTS: Targeting feeds pre-sorted by click volume and traffic interaction
RSS_FEEDS = {
    "Politico (Most Popular)": "https://rsshub.app",
    "Axios (Trending news)": "https://rsshub.app",
    "The Points Guy (Latest Offers)": "https://thepointsguy.com/feed/"
}

def fetch_rss_content():
    sections = {name: [] for name in RSS_FEEDS}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for source_name, url in RSS_FEEDS.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                
                # Capture exactly the top 3 highest-ranked items inside the pre-sorted feed
                for entry in feed.entries[:3]:
                    title = entry.title
                    link = entry.link
                    summary = entry.get('summary', entry.get('description', ''))
                    
                    clean_soup = BeautifulSoup(summary, 'html.parser')
                    text_snippet = clean_soup.get_text().strip()
                    
                    if len(text_snippet) > 240:
                        text_snippet = text_snippet[:240] + "..."
                        
                    sections[source_name].append(f"### [{title}]({link})\n{text_snippet}\n")
            else:
                sections[source_name].append(f"* Connection error ({response.status_code}) fetching updates.")
        except Exception as e:
            sections[source_name].append(f"* Feed parsing momentarily offline.")
            
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
