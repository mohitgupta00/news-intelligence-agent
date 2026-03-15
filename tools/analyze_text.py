from typing import Optional
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from tools.fetch_news import fetch_news

_groq_client = None

def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client

def analyze_with_groq(prompt: str) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000
    )
    return response.choices[0].message.content or ""

def _analyze_with_best_model(prompt: str) -> str:
    """Use Groq for all analysis tasks."""
    return analyze_with_groq(prompt)

def summarize_articles(articles_text: str) -> str:
    prompt = f"""You are a news analyst. Provide a concise summary of the following news articles.

Articles:
{articles_text}

Summary:"""
    return _analyze_with_best_model(prompt)

def analyze_sentiment(articles_text: str) -> str:
    prompt = f"""You are a sentiment analyst. Analyze the overall sentiment and tone of these news articles.

Articles:
{articles_text}

Provide:
1. Overall sentiment (Positive/Negative/Neutral)
2. Key emotional themes
3. Confidence level (high/medium/low)

Sentiment Analysis:"""
    return _analyze_with_best_model(prompt)

def extract_entities(articles_text: str) -> str:
    prompt = f"""Extract all named entities (people, organizations, locations, products) from these news articles.

Articles:
{articles_text}

List each entity with its type:"""
    return _analyze_with_best_model(prompt)

def analyze_timeline(query: str) -> str:
    news_result, source = fetch_news(query, n=10)
    if not news_result:
        return ""
    
    prompt = f"""Extract a chronological timeline of key events from these news articles about "{query}".
Format as: [DATE if available] - [EVENT]
Sort events chronologically (oldest to newest).
If dates are not available, infer relative timing from the article context.

Articles:
{news_result}

Timeline:"""
    return _analyze_with_best_model(prompt)

def analyze_text(query: str, task: str, articles_text: str = "") -> str:
    if task == "summarize":
        return summarize_articles(articles_text) if articles_text else "No articles to summarize."
    elif task == "sentiment":
        return analyze_sentiment(articles_text) if articles_text else "No articles for sentiment analysis."
    elif task == "extract_entities":
        return extract_entities(articles_text) if articles_text else "No articles to extract entities from."
    elif task == "timeline":
        return analyze_timeline(query) if query else "No query provided for timeline."
    else:
        return f"Unknown task: {task}"
