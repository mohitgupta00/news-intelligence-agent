import os

GROQ_API_KEY    = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY")  # Optional
NEWSAPI_KEY     = os.environ.get("NEWSAPI_KEY")
GNEWS_KEY       = os.environ.get("GNEWS_KEY")
NEWSDATA_KEY    = os.environ.get("NEWSDATA_KEY")
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")

GROQ_MODEL    = os.environ.get("GROQ_MODEL",    "llama-3.1-8b-instant")
GEMINI_MODEL  = os.environ.get("GEMINI_MODEL",  "gemini-2.0-flash-exp")  # Optional
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 600))

# LangSmith Observability (fixes typo: LANCHAIN -> LANGCHAIN)
if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"]  = "true"
    os.environ["LANGCHAIN_API_KEY"]     = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"]     = os.environ.get("LANGCHAIN_PROJECT", "newsiq-agent")

if not all([GROQ_API_KEY, NEWSAPI_KEY]):
    raise ValueError(
        "Missing required API keys. Set: GROQ_API_KEY, NEWSAPI_KEY. "
        "Optional: GEMINI_API_KEY, GNEWS_KEY, NEWSDATA_KEY, LANGSMITH_API_KEY"
    )
