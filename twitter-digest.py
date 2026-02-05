#!/usr/bin/env python3

import os
import smtplib
import tweepy
from email.mime.text import MIMEText
from email.utils import formataddr
from datetime import datetime, timedelta
from pathlib import Path

import anthropic

# load .env file if it exists
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value.strip('"').strip("'")

def fetch_twitter_timeline():
    """fetch home timeline from last 24 hours"""
    
    # authenticate with twitter api v2
    client = tweepy.Client(
        bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    
    # get authenticated user
    me = client.get_me()
    user_id = me.data.id
    
    # calculate 24 hours ago
    start_time = datetime.utcnow() - timedelta(days=1)
    # free tier = 100 posts/month. daily runs = 30/month, so 100/30 ≈ 3 per run
    max_results = int(os.getenv("TWITTER_MAX_RESULTS", "3"))

    # fetch home timeline
    tweets = client.get_home_timeline(
        max_results=min(max_results, 100),
        start_time=start_time,
        tweet_fields=['created_at', 'public_metrics', 'author_id'],
        expansions=['author_id'],
        user_fields=['name', 'username']
    )
    
    if not tweets.data:
        return "no tweets found in the last 24 hours."
    
    # format tweets with engagement scores
    users = {user.id: user for user in tweets.includes.get('users', [])}
    
    tweet_list = []
    for tweet in tweets.data:
        author = users.get(tweet.author_id)
        if author:
            # calculate engagement score (likes + retweets * 2)
            engagement = tweet.public_metrics['like_count'] + (tweet.public_metrics['retweet_count'] * 2)
            tweet_list.append({
                'username': author.username,
                'name': author.name,
                'text': tweet.text,
                'likes': tweet.public_metrics['like_count'],
                'retweets': tweet.public_metrics['retweet_count'],
                'engagement': engagement
            })
    
    # sort by engagement (highest first)
    tweet_list.sort(key=lambda x: x['engagement'], reverse=True)
    
    # format tweets
    formatted = []
    for t in tweet_list:
        formatted.append(
            f"@{t['username']} ({t['name']}):\n"
            f"{t['text']}\n"
            f"[{t['likes']} likes, {t['retweets']} retweets]"
        )
    
    return "\n\n---\n\n".join(formatted)


def main():
    """main execution"""
    try:
        print("fetching twitter timeline from last 24 hours...")
        tweets = fetch_twitter_timeline()
        
        if tweets == "no tweets found in the last 24 hours.":
            send_email(tweets)
            print("no tweets; sent short message to email")
            return
        
        # format for claude with summarization prompt
        prompt = f"""here are tweets from my twitter feed in the last 24 hours (sorted by engagement/traction). 

create a concise daily digest focusing on:

1. **major themes & news**: what are the big things happening? (focus on high-traction tweets)
2. **direct quotes**: include memorable/insightful quotes, especially from smaller accounts (likely friends/peers)
3. **key updates**: important announcements or developments

guidelines:
- DO NOT include all tweets - just summarize the major topics
- weight your summary towards high-engagement posts (more likes/retweets = more important)
- include direct quotes when they're particularly good, especially from personal connections
- keep it conversational and brief (2-3 short paragraphs)

---

{tweets}"""

        # summarize via anthropic api
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = msg.content[0].text

        # send email
        send_email(summary)
        print("digest sent to email")
        return summary

    except Exception as e:
        print(f"error fetching twitter digest: {e}")
        raise


def send_email(body: str) -> None:
    """send digest via gmail smtp"""
    from_addr = os.getenv("EMAIL_FROM")
    password = os.getenv("EMAIL_APP_PASSWORD")
    to_addr = os.getenv("EMAIL_TO")
    if not all([from_addr, password, to_addr]):
        raise ValueError("EMAIL_FROM, EMAIL_APP_PASSWORD, and EMAIL_TO must be set")

    subject = f"Twitter digest - {datetime.now().strftime('%Y-%m-%d')}"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_addr, password)
        server.sendmail(from_addr, to_addr, msg.as_string())


if __name__ == "__main__":
    main()
