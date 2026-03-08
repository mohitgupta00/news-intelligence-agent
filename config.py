import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
GNEWS_KEY = os.environ.get("GNEWS_KEY")
NEWSDATA_KEY = os.environ.get("NEWSDATA_KEY")

LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")

GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 600))

if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY
if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
if LANGSMITH_API_KEY:
    os.environ["LANGSMITH_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANCHAIN_TRACING_V2"] = "true"

if not all([GROQ_API_KEY, NEWSAPI_KEY]):
    raise ValueError(
        "Missing required API keys. Please set environment variables: "
        "GROQ_API_KEY, NEWSAPI_KEY. "
        "Optional: GEMINI_API_KEY, GNEWS_KEY, NEWSDATA_KEY, LANGSMITH_API_KEY"
    )
