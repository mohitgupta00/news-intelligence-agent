# NewsIQ — AI-Powered News Intelligence System

A multi-agent news intelligence system built with LangGraph where an LLM Orchestrator dynamically plans and routes queries across specialized tools, maintaining session memory for conversational follow-ups.

## Features

- **Intelligent Orchestration** — LLM-powered intent detection (summarize, sentiment, timeline, compare, extract_entities)
- **Dynamic Tool Routing** — Automatically selects the right tool based on query intent
- **Session Memory** — Remembers entities and context across follow-up questions
- **Parallel Execution** — Uses LangGraph Send API for independent task parallelization
- **Smart Caching** — Reuses previously fetched results to minimize API calls
- **Follow-up Optimization** — Detects when answers can come from memory without new API calls
- **Graceful Failure** — Replanner retries with broader queries; out-of-scope detection

## Architecture

```
User Query → Query Resolver → Query Rewriter → Planner → Router
                                                            ↓
                                              ┌─────────────┴─────────────┐
                                              ↓             ↓             ↓
                                        fetch_news   analyze_text   compare_entities
                                              ↓             ↓             ↓
                                          Step Collector ←────────────────
                                              ↓
                                           Replanner
                                              ↓
                                          Synthesizer → Final Answer
```

## Tech Stack

- **Orchestration**: LangGraph
- **LLM**: Groq (planning), Gemini (analysis)
- **UI**: Streamlit
- **News Sources**: NewsAPI, GNews, NewsData.io

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/newsiq.git
cd newsiq
```

### 2. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
# Required
GROQ_API_KEY=your_groq_api_key
NEWSAPI_KEY=your_newsapi_key

# Optional
GEMINI_API_KEY=your_gemini_api_key
GNEWS_KEY=your_gnews_key
NEWSDATA_KEY=your_newsdata_key
LANGSMITH_API_KEY=your_langsmith_key
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Locally

```bash
streamlit run ui/app.py
```

Or with Docker:

```bash
docker compose up --build
```

Then open http://localhost:8501

## Deployment

### Streamlit Community Cloud (Recommended)

1. Push to GitHub (public repo)
2. Go to https://share.streamlit.io
3. Connect your GitHub repo
4. Add API keys in Settings → Secrets
5. Deploy

Your app will be available at `https://your-app-name.streamlit.app`

## Usage Examples

| Query | Intent | Tool Used |
|-------|--------|-----------|
| "Summarize OpenAI news" | summarize | fetch_news → analyze_text |
| "What's sentiment around Tesla?" | sentiment | fetch_news → analyze_text |
| "Compare Google and Microsoft" | compare | compare_entities |
| "Timeline of SpaceX events" | timeline | fetch_news → analyze_text |

## Session Memory Demo

```
User: "Summarize news about Sam Altman"
  → Normal flow with fetch_news + analyze_text

User: "What's the sentiment around him?"  
  → Pronoun resolved from memory, NO new fetch needed

User: "Which one had more positive coverage?"
  → Answered from memory, ZERO API calls
```

## Project Structure

```
newsiq/
├── ui/
│   └── app.py              # Streamlit entry point
├── graph/
│   ├── state.py            # Typed state definition
│   ├── nodes.py            # All agent nodes
│   ├── edges.py            # Conditional routing
│   └── builder.py          # LangGraph construction
├── tools/
│   ├── fetch_news.py       # Multi-source news fetching
│   ├── analyze_text.py     # Text analysis tools
│   └── compare_entities.py # Entity comparison
├── memory/
│   └── checkpointer.py     # Session persistence
├── config.py               # Configuration
├── Dockerfile              # Container definition
└── docker-compose.yml      # Local dev setup
```

## License

MIT

## Credits

Built with [LangGraph](https://langchain-ai.github.io/langgraph/), [Streamlit](https://streamlit.io/), and [Groq](https://groq.com/).
