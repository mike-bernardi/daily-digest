# 🌅 My Personal AI-Curated Daily Digest

A private, automated, and serverless daily newsletter website built entirely with Python, GitHub Actions, and Google Gemini. 

Every morning, a background runner fetches my custom RSS feeds, uses AI to distill the articles into 2-sentence summaries, and rewrites the homepage dynamically.

## 🚀 Live Website
👉 **[View My Live Daily Digest](https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO_NAME/)**  
*(Note: Replace the link above with your actual GitHub Pages URL so you can open it with one tap from your phone)*

## 🛠️ Architecture
- **Data Gathering:** Python `feedparser` collects items from curated RSS endpoints.
- **AI Synthesis:** Google `Gemini 2.5 Flash` scores, filters, and formats the raw feeds into clean Markdown.
- **Automation Engine:** GitHub Actions cron trigger wakes up every morning at 7:00 AM UTC.
- **Hosting:** GitHub Pages deploys the updated `index.md` file instantly as a static website.

## 🔧 Maintenance & Manual Updates
If I ever want to force a refresh on my phone without waiting for the morning cron schedule:
1. Navigate to the **Actions** tab in this repository.
2. Tap **Daily AI Digest Website** on the left menu.
3. Click the **Run workflow** dropdown button and tap the green confirmation button.

