import os
import smtplib
from email.message import EmailMessage
import yfinance as yf
import feedparser
import urllib.parse
from anthropic import Anthropic
import datetime
from dotenv import load_dotenv
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# --- Configuration ---
TICKERS_FILE = "tickers.txt"
DAYS_BACK = 7

# --- Prompts ---
SYSTEM_INSTRUCTION = """
You are a fundamental analyst for a long-term moat investor. Your job is to summarize weekly news for a company based on the provided news headlines and snippets.
Strictly adhere to the following rules:
1. Ignore and filter out any news regarding daily stock price movements, analyst upgrades/downgrades, macroeconomic speculation, options flow, or generic market noise.
2. Only summarize news related to core business fundamentals, product developments, leadership changes, shifts in the company's economic moat, competitive landscape, or significant legal/regulatory events.
3. CRITICAL: If there is any news regarding official quarterly or annual earnings reports, this is of utmost importance. You MUST highlight the earnings data prominently at the top of the summary for that company.
4. Keep the summary concise, focusing on actionable fundamental insights. Use bullet points.
5. If a company has only "noisy" news and no material business developments for the week, reply exactly with: "No material business developments this week."
6. Format your output in clean HTML without markdown wrappers (e.g., use <ul>, <li>, <strong>, etc.). Do not include ```html blocks.
"""

def get_tickers():
    if not os.path.exists(TICKERS_FILE):
        print(f"Error: {TICKERS_FILE} not found.")
        return []
    with open(TICKERS_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def get_company_name(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        name = info.get('shortName', ticker)
        return name
    except Exception as e:
        print(f"Could not fetch company name for {ticker}: {e}")
        return ticker

def fetch_google_news(company_name, days_back=7):
    query = f'"{company_name}" when:{days_back}d'
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(url)
    articles = []
    
    for entry in feed.entries[:15]:
        articles.append({
            "title": entry.title,
            "published": entry.published,
            "link": entry.link
        })
    return articles

def summarize_news(company_name, articles, client, model):
    if not articles:
        return "<p>No news articles found this week.</p>"
    
    news_content = ""
    for idx, article in enumerate(articles, 1):
        news_content += f"{idx}. {article['title']}\n"
    
    prompt = f"Company: {company_name}\n\nRecent News Headlines:\n{news_content}\n\nPlease summarize these based on your system instructions."
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_INSTRUCTION,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"<p>Error generating summary: {e}</p>"

def send_email(html_content, sender, password, recipient, server, port):
    msg = EmailMessage()
    msg['Subject'] = f"Weekly Moat Investor Summary - {datetime.date.today()}"
    msg['From'] = sender
    msg['To'] = recipient
    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(html_content, subtype='html')

    try:
        if port == 465:
            with smtplib.SMTP_SSL(server, port) as smtp:
                smtp.login(sender, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(server, port) as smtp:
                smtp.starttls()
                smtp.login(sender, password)
                smtp.send_message(msg)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def run_summary():
    print(f"\n[{datetime.datetime.now()}] Running weekly summary task...")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
    
    if not api_key or api_key == "your_anthropic_key_here":
        print("ANTHROPIC_API_KEY is not set. Exiting task.")
        return

    email_sender = os.environ.get("EMAIL_SENDER")
    email_password = os.environ.get("EMAIL_PASSWORD")
    email_recipient = os.environ.get("EMAIL_RECIPIENT")
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 465))

    is_local_test = not (email_sender and email_password and email_recipient) or email_sender == "your_email@gmail.com"
    
    client = Anthropic(api_key=api_key)
    tickers = get_tickers()
    
    if not tickers:
        print("No tickers to process.")
        return

    full_html_report = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: auto; }
            h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; }
            .company-section { margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <h1>Weekly Moat Investor Summary</h1>
    """

    for ticker in tickers:
        print(f"Processing {ticker}...")
        company_name = get_company_name(ticker)
        print(f"  Company Name: {company_name}")
        
        articles = fetch_google_news(company_name, DAYS_BACK)
        print(f"  Fetched {len(articles)} articles.")
        
        summary_html = summarize_news(company_name, articles, client, model)
        
        full_html_report += f"""
        <div class="company-section">
            <h2>{company_name} ({ticker})</h2>
            {summary_html}
        </div>
        """

    full_html_report += "</body></html>"

    if is_local_test:
        print("\n" + "="*50)
        print("HTML REPORT GENERATED:")
        print("="*50 + "\n")
        print(full_html_report)
        
        with open("local_report.html", "w", encoding="utf-8") as f:
            f.write(full_html_report)
        print("\nReport also saved to 'local_report.html'.")
    else:
        print("Sending email...")
        send_email(full_html_report, email_sender, email_password, email_recipient, smtp_server, smtp_port)

def main():
    load_dotenv()
    print("Weekly Summarizer Bot starting...")
    
    # Run once immediately on startup if you want to test, or just schedule it. 
    # For now, we will just schedule it for every Friday at 18:00
    scheduler = BlockingScheduler()
    # Schedule for every Friday at 18:00 (6 PM)
    scheduler.add_job(run_summary, CronTrigger(day_of_week='fri', hour=18))
    
    print("Scheduler started. Waiting for next run (Friday 18:00).")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down scheduler.")

if __name__ == "__main__":
    main()
