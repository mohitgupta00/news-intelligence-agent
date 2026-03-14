import re, json, hashlib, time, asyncio, logging
from typing import Any, Optional, Literal
from groq import Groq
from langchain_groq import ChatGroq
from pydantic import BaseModel
import config
from config import GROQ_API_KEY, GROQ_MODEL, CACHE_TTL_SECONDS
from graph.state import NewsIQState
from tools.fetch_news import fetch_news_async, _is_likely_hallucinated
from tools.analyze_text import summarize_articles, analyze_sentiment, extract_entities, analyze_timeline, _analyze_with_best_model
from tools.compare_entities import compare_entities

logger=logging.getLogger(__name__)
_groq_client=Groq(api_key=GROQ_API_KEY)
_chat_groq=ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.1)

# LLM cache (module-level OK - per-process)
_llm_cache={}
_LLM_CACHE_TTL=600
def _llm_cache_key(p): return hashlib.md5(f"{GROQ_MODEL}:{p}".encode()).hexdigest()
def _get_llm_cache(p):
    k=_llm_cache_key(p)
    if k in _llm_cache:
        ts,val=_llm_cache[k]
        if time.time()-ts<_LLM_CACHE_TTL: return val
    return None
def _set_llm_cache(p,v): _llm_cache[_llm_cache_key(p)]=(time.time(),v)

# spaCy NER setup
try:
    import spacy
    _nlp=spacy.load("en_core_web_sm")
    _SPACY_OK=True
except OSError:
    _nlp=None
    _SPACY_OK=False
    logger.warning("spaCy model missing. Run: python -m spacy download en_core_web_sm")

# Sentence-transformer embedder for PRIOR-check
_embedder=None
def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder=SentenceTransformer("all-MiniLM-L6-v2")
        except: pass
    return _embedder

def _cosine(a,b):
    import numpy as np
    a,b=np.array(a,dtype=float),np.array(b,dtype=float)
    return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-8))

def _prior_covers_query(query,last_result,threshold=0.82):
    """Cosine similarity check - replaces expensive LLM call."""
    if not last_result: return False
    embedder=_get_embedder()
    if embedder:
        embs=embedder.encode([query,last_result[:400]])
        return _cosine(embs[0],embs[1])>=threshold
    # Keyword fallback
    def tok(t): return set(re.findall(r'\b\w{3,}\b',t.lower()))
    q_toks=tok(query)
    return len(q_toks&tok(last_result[:400]))/max(len(q_toks),1)>=0.45

# Pydantic schema for query_rewriter
class QueryAnalysis(BaseModel):
    intent: Literal["summarize","sentiment","timeline","compare","extract_entities"]
    api_queries: list[str]

# NER entity extraction
class _NEROutput(BaseModel):
    entities: list[str]

def extract_entities_from_query(query):
    """spaCy NER -> Groq structured fallback -> heuristic."""
    if _SPACY_OK and _nlp:
        doc=_nlp(query)
        ents=[e.text for e in doc.ents if e.label_ in ("ORG","PERSON","GPE","PRODUCT","EVENT","NORP")]
        if ents: return ents[:5]
    try:
        structured=_chat_groq.with_structured_output(_NEROutput)
        result=structured.invoke(f"Extract named entities (people,orgs,places,products) from: \"{query}\". Return only entity strings.")
        if result.entities: return result.entities[:5]
    except: pass
    words=query.split()
    return [w.strip("'\",." for w in words if len(w)>3 and w[0].isupper() and w not in {"What","Where","When","Who","Why","How","The","This","That","These","Those","Will","Does"}][:5]

# Temporal helpers
TEMPORAL_PATTERNS=[r'this\s+(week|month|year|day)',r'latest\s+news',r'recent',r'latest',r'today',r'yesterday',r'past\s+\d+\s+(days?|weeks?|months?|years?)',r'last\s+\d+\s+(days?|weeks?|months?|years?)']
PRONOUN_PATTERNS=[r'\b(it|this|that|them|their|these)\b',r'\b(one|which)\b']

def extract_temporal_constraint(query):
    for p in TEMPORAL_PATTERNS:
        m=re.search(p,query.lower())
        if m: return m.group(0)
    return None

def contains_pronoun_reference(query):
    return any(re.search(p,query.lower()) for p in PRONOUN_PATTERNS)

# OOS patterns
_OOS_PATTERNS=[r'stock\s*(price|value)',r'predict.*price',r'forecast.*stock',r'will.*go\s+(up|down)',r'price.*will',r'how much.*will.*(cost|be worth)',r'investment.*advice',r'should\s+I\s+(buy|sell)']

# guard_node (NEW)
def guard_node(state):
    """Dedicated OOS gate between query_rewriter and planner."""
    query_lower=state["resolved_query"].lower()
    if any(re.search(p,query_lower) for p in _OOS_PATTERNS):
        return {"replan_decision":"out_of_scope"}
    return {"replan_decision":None}

# turn_initializer
def turn_initializer(state):
    """Resets per-turn state."""
    return {"plan":[],"step_outputs":{},"session_cache":{},"current_step":0,"replan_count":0,"replan_decision":None,"final_answer":None,"planning_done":False,"temporal_constraint":None,"api_queries":[],"intent":""}

# query_resolver
def query_resolver(state):
    em=state["entity_memory"]
    query=state["user_query"]
    temporal=extract_temporal_constraint(query)
    last_entity=em.get("last_entity","")
    last_entities=em.get("last_entities",[])
    last_task=em.get("last_task","")
    needs_res=contains_pronoun_reference(query)
    if not last_entity or not needs_res: resolved=query
    else:
        context=f"Previous entities: {', '.join(last_entities) if last_entities else last_entity}"
        prompt=f"{context}\nLast task: {last_task}\nCurrent query: \"{query}\"\nRewrite to be fully self-contained. Return only the rewritten string."
        cached=_get_llm_cache(prompt)
        if cached: resolved=cached
        else:
            resp=_groq_client.chat.completions.create(model=GROQ_MODEL,messages=[{"role":"user","content":prompt}],temperature=0.1)
            resolved=(resp.choices[0].message.content or query).strip()
            _set_llm_cache(prompt,resolved)
    return {"resolved_query":resolved,"temporal_constraint":temporal}

# query_rewriter (structured output)
def query_rewriter(state):
    resolved=state["resolved_query"]
    structured=_chat_groq.with_structured_output(QueryAnalysis)
    prompt=f"Analyze user query and determine:\n1. intent: summarize|sentiment|timeline|compare|extract_entities\n2. api_queries: 1-3 clean 2-5 word keyword strings\n\nCRITICAL: for compare queries with 2 entities, produce EXACTLY 2 separate queries.\n\nExamples:\n  'Compare Google and Microsoft' -> intent=compare, api_queries=['Google news','Microsoft news']\n  'Summarize latest OpenAI news' -> intent=summarize, api_queries=['OpenAI news']\n\nUser query: \"{resolved}\""
    try:
        result=structured.invoke(prompt)
        return {"intent":result.intent,"api_queries":result.api_queries or [resolved]}
    except Exception as e:
        logger.warning(f"query_rewriter error: {e}")
        return {"intent":"summarize","api_queries":[resolved]}

# planner
def planner(state):
    if state.get("planning_done") and state.get("plan"): return {"planning_done":True}
    resolved=state["resolved_query"]
    api_queries=state.get("api_queries",[resolved])
    intent=state.get("intent","summarize")
    temporal=state.get("temporal_constraint","") or ""
    tsuffix=f" {temporal}" if temporal else ""
    if intent=="compare" and len(api_queries)==2:
        plan=[{"step":0,"tool":"compare_entities","params":{"entity_a":api_queries[0],"entity_b":api_queries[1]},"depends_on":[]}]
    elif intent=="timeline":
        plan=[{"step":0,"tool":"fetch_news","params":{"query":api_queries[0]+tsuffix,"n":7},"depends_on":[]},{"step":1,"tool":"analyze_text","params":{"task":"timeline"},"depends_on":[0]}]
    elif intent in ("summarize","sentiment","extract_entities"):
        plan=[{"step":i,"tool":"fetch_news","params":{"query":q,"n":5},"depends_on":[]} for i,q in enumerate(api_queries)]
        plan.append({"step":len(api_queries),"tool":"analyze_text","params":{"task":intent},"depends_on":list(range(len(api_queries)))})
    else:
        plan=[{"step":0,"tool":"fetch_news","params":{"query":api_queries[0]+tsuffix,"n":5},"depends_on":[]},{"step":1,"tool":"analyze_text","params":{"task":"summarize"},"depends_on":[0]}]
    return {"plan":plan,"current_step":0,"replan_count":0}

# router
def router(state):
    from langgraph.constants import Send
    ready=[s for s in state["plan"] if s["step"] not in state["step_outputs"] and all(dep in state["step_outputs"] for dep in s.get("depends_on",[]))]
    return [Send(s["tool"],{"step":s,"state":state}) for s in ready]

# fetch_news_node (async)
async def fetch_news_node(state):
    if "step" in state: step,full_state=state["step"],state["state"]
    else:
        pending=[s for s in state.get("plan",[]) if s["step"] not in state.get("step_outputs",{})]
        if not pending: return {"step_outputs":{}}
        step,full_state=pending[0],state
    query=step["params"].get("query","")
    n=step["params"].get("n",5)
    session_cache=dict(full_state.get("session_cache",{}))
    cache_key=f"fetch::{query}::{n}"
    if cache_key in session_cache:
        cached_val,cached_ts=session_cache[cache_key]
        if time.time()-cached_ts<CACHE_TTL_SECONDS and not _is_likely_hallucinated(cached_val):
            result,source=cached_val,"cache"
        else: result,source=await fetch_news_async(query,n)
    else: result,source=await fetch_news_async(query,n)
    if result: session_cache[cache_key]=(result,time.time())
    existing=dict(full_state.get("step_outputs",{}))
    existing[step["step"]]={"step_index":step["step"],"tool":"fetch_news","params":step["params"],"result":result,"status":"success" if result else "empty","source":source}
    return {"step_outputs":existing,"session_cache":session_cache}

# analyze_text_node
def analyze_text_node(state):
    if "step" in state: step,full_state=state["step"],state["state"]
    else:
        pending=[s for s in state.get("plan",[]) if s["step"] not in state.get("step_outputs",{})]
        if not pending: return {"step_outputs":{}}
        step,full_state=pending[0],state
    task=step["params"].get("task","summarize")
    dep_outputs=[full_state["step_outputs"][dep]["result"] for dep in step.get("depends_on",[]) if full_state["step_outputs"].get(dep,{}).get("result")]
    articles_text="\n\n".join(dep_outputs)
    if task=="timeline": result=analyze_timeline(step["params"].get("query",full_state.get("resolved_query","")))
    elif task=="summarize": result=summarize_articles(articles_text)
    elif task=="sentiment": result=analyze_sentiment(articles_text)
    elif task=="extract_entities": result=extract_entities(articles_text)
    else: result=f"Unknown task: {task}"
    existing=dict(full_state.get("step_outputs",{}))
    existing[step["step"]]={"step_index":step["step"],"tool":"analyze_text","params":step["params"],"result":result,"status":"success"}
    return {"step_outputs":existing}

# compare_entities_node
def compare_entities_node(state):
    if "step" in state: step,full_state=state["step"],state["state"]
    else:
        pending=[s for s in state.get("plan",[]) if s["step"] not in state.get("step_outputs",{})]
        if not pending: return {"step_outputs":{}}
        step,full_state=pending[0],state
    entity_a=step["params"].get("entity_a","")
    entity_b=step["params"].get("entity_b","")
    result=compare_entities(entity_a,entity_b,state=full_state)
    existing=dict(full_state.get("step_outputs",{}))
    existing[step["step"]]={"step_index":step["step"],"tool":"compare_entities","params":step["params"],"result":result,"status":"success"}
    return {"step_outputs":existing}

# step_collector (no polling)
def step_collector(state):
    """LangGraph guarantees all Send results merged."""
    return {"all_steps_complete":True}

# replanner
def replanner(state):
    any_empty=any(v.get("status")=="empty" for v in state["step_outputs"].values())
    replan_count=state.get("replan_count",0)
    max_retries=2
    if replan_count>=max_retries: return {"replan_decision":"finish"}
    if any_empty and replan_count<max_retries:
        failed_queries=[s["params"].get("query","") for s in state["plan"]]
        original=state.get("resolved_query",state.get("user_query",""))
        prompt=f"You are a query recovery specialist.\nORIGINAL: \"{original}\"\nFAILED: {json.dumps(failed_queries)}\nProvide 2-3 recovery strategies. Return ONLY JSON array: [{{\"step\":1,\"tool\":\"fetch_news\",\"params\":{{\"query\":\"...\"}}}}]"
        try:
            resp=_groq_client.chat.completions.create(model=GROQ_MODEL,messages=[{"role":"user","content":prompt}],temperature=0.1)
            content=resp.choices[0].message.content
            match=re.search(r'\[[\s\S]*\]',content)
            if not match: return {"replan_decision":"finish"}
            new_steps=json.loads(match.group())
            attempted={s["params"].get("query","").lower() for s in state["plan"]}
            filtered=[s for s in new_steps if s.get("params",{}).get("query","").lower() not in attempted]
            if not filtered: return {"replan_decision":"finish"}
            offset=len(state["plan"])
            for i,s in enumerate(filtered): s["step"]=offset+i
            return {"plan":state["plan"]+filtered,"replan_count":replan_count+1,"replan_decision":"continue"}
        except Exception as e:
            logger.error(f"Replanner error: {e}")
    return {"replan_decision":"finish"}

# synthesizer
def _build_response(final,state):
    entities=extract_entities_from_query(state["resolved_query"])
    return {"final_answer":final,"entity_memory":{"last_entity":entities[0] if entities else state["entity_memory"].get("last_entity"),"last_entities":entities,"last_task":state.get("intent"),"last_result":final},"messages":[{"role":"assistant","content":final}]}

def synthesizer(state):
    resolved=state.get("resolved_query",state.get("user_query",""))
    intent=state.get("intent","summarize")
    entity_memory=state.get("entity_memory",{})
    step_outputs=state.get("step_outputs",{})
    if state.get("replan_decision")=="out_of_scope":
        return _build_response("I'm a news analysis assistant and don't handle prediction questions like stock prices or investment advice. I can help with news summaries, sentiment analysis, entity comparisons, and timelines. Try that?",state)
    all_empty=all(v.get("status")=="empty" for v in step_outputs.values()) if step_outputs else True
    if all_empty: return _build_response("I wasn't able to find news articles about this query. Try rephrasing.",state)
    last_result=entity_memory.get("last_result","")
    if last_result and _prior_covers_query(resolved,last_result):
        prior_prompt=f"Answer this question using only the prior result below.\nQuestion: {resolved}\nPrior result: {last_result}\nGive a direct, concise answer."
        return _build_response(_analyze_with_best_model(prior_prompt),state)
    all_results=[f"Step {k} ({v.get('tool','?')}): {v.get('result','')}" for k,v in sorted(step_outputs.items())]
    combined="\n\n".join(all_results)
    prior_ctx=""
    for pe in state.get("prior_entity_results",[]):
        prior_ctx+=f"- {pe['entity']}: {pe['result'][:500]}\n"
    if prior_ctx: combined+=f"\n\nPrevious context:\n{prior_ctx}"
    prompt=f"Original query: {resolved}\n\nResearch outputs:\n{combined}\n\nWrite a clear, structured answer. Be concise but informative."
    return _build_response(_analyze_with_best_model(prompt),state)

def infer_task(plan):
    for step in plan:
        tool=step.get("tool","")
        if tool=="analyze_text": return step.get("params",{}).get("task","unknown")
        if tool=="compare_entities": return "compare"
    return "unknown"
