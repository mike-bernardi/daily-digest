import os
import feedparser
import requests
from bs4 import BeautifulSoup
from google import genai
import datetime

# Your customized feeds
RSS_FEEDS = {
    "Politico": "https://politico.com",
    "Axios": "https://axios.com",
    "The Points Guy": "https://thepointsguy.com"
}

def fetch_rss_content():
    combined_text = []
    for source_name, url in RSS_FEEDS.items():
        combined_text.append(f"=== Source: {source_name} ===")
        feed = feedparser.parse(url)
        # Pull the top 4 freshest articles per source
        for entry in feed.entries[:4]:
            summary = entry.get('summary', entry.get('description', 'No summary available.'))
            combined_text.append(f"Title: {entry.title}\nLink: {entry.link}\nSummary: {summary}\n")
    return "\n".join(combined_text)

def fetch_chicago_events():
    """Scrapes upcoming local event listings for Chicago."""
    try:
        url = "https://choosechicago.com"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        events = []
        # Target standard event cards or headings commonly used on local listing layouts
        for card in soup.find_all(['h3', 'h4'], class_=['card-title', 'event-title'], limit=8):
            title = card.get_text(strip=True)
            link_tag = card.find('a') or card.find_parent('a')
            link = link_tag['href'] if link_tag and link_tag.has_attr('href') else url
            if not link.startswith('http'):
                link = f"https://www.choosechicago.com{link}"
            events.append(f"Event: {title}\nLink: {link}")
            
        if not events:
            return "No specific automated events found today. Prompt AI to suggest standard seasonal happenings."
        return "\n".join(events)
    except Exception as e:
        return f"Could not fetch Chicago events right now: {str(e)}"

def generate_digest(news_content, chicago_content):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    today_str = datetime.date.today().strftime("%B %d, %Y")
    
    prompt = f"""
    You are my elite personal news editor and concierge. Take the raw inputs below and output a beautiful, highly polished Markdown document for my personal website.
    
    Start with the title '# 🌅 My Daily Briefing - {today_str}'.
    
    Structure the page strictly with these three main headers:
    1. '## 🏛️ National News (Politico & Axios)'
       - Synthesize the most critical political trends into 3 brief bullet points.
       - Include direct markdown links to read deeper.
    2. '## ✈️ Points, Miles & Travel (The Points Guy)'
       - Summarize credit card bonuses, flight updates, or airline promos in a punchy style.
       - Always include the hyperlinked article titles.
    3. '## 🎭 What to Do in Chicago'
       - Highlight upcoming tours, concerts, festivals, or local activities mentioned in the data.
       - Ensure a sophisticated, fun tone tailored to an active city explorer.

    Do not include any code block wrappers like ```markdown or ```html. Go straight into the content.
    
    RAW NATIONAL NEWS DATA:
    {news_content}
    
    RAW CHICAGO EVENTS DATA:
    {chicago_content}
    """
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    return response.text

if __name__ == "__main__":
    print("Reading RSS feeds...")
    news_data = fetch_rss_content()
    
    print("Gathering Chicago events...")
    chicago_data = fetch_chicago_events()
    
    print("Synthesizing with Gemini...")
    final_markdown = generate_digest(news_data, chicago_data)
    
    print("Writing index.md...")
    with open("index.md", "w", encoding="utf-8") as f:
        f.write(final_markdown)
        
    print("Success! Ready for GitHub Pages to deploy.")
