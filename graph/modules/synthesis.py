"""Synthesis node: final response generation with RAG-based context extraction."""

import re
from tools.analyze_text import _analyze_with_best_model
from utils.text_processing import extract_relevant_chunks

def _prior_covers_query(query, last_result, threshold=0.82):
    """Check if prior result covers current query using similarity."""
    if not last_result:
        return False
    
    try:
        from utils.text_processing import get_embedder, cosine_similarity
        embedder = get_embedder()
        if embedder:
            embeddings = embedder.encode([query, last_result[:400]])
            return cosine_similarity(embeddings[0], embeddings[1]) >= threshold
    except:
        pass
    
    # Keyword fallback
    def tokenize(text):
        return set(re.findall(r'\b\w{3,}\b', text.lower()))
    
    query_tokens = tokenize(query)
    result_tokens = tokenize(last_result[:400])
    
    if not query_tokens:
        return False
    
    overlap = len(query_tokens & result_tokens)
    return overlap / len(query_tokens) >= 0.45

def extract_entities_from_query(query):
    """Extract named entities from query using spaCy or fallback methods."""
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(query)
        entities = [
            ent.text for ent in doc.ents
            if ent.label_ in ("ORG", "PERSON", "GPE", "PRODUCT", "EVENT", "NORP")
        ]
        if entities:
            return entities[:5]
    except:
        pass
    
    # Fallback: simple heuristic
    words = query.split()
    entities = [
        word.strip("'\",.") for word in words
        if (len(word) > 3 and word[0].isupper() 
            and word not in {"What", "Where", "When", "Who", "Why", "How", 
                           "The", "This", "That", "These", "Those", "Will", "Does"})
    ]
    return entities[:5]

def _build_response(final_answer, state):
    """Build final response with entity memory update."""
    entities = extract_entities_from_query(state["resolved_query"])
    
    return {
        "final_answer": final_answer,
        "entity_memory": {
            "last_entity": entities[0] if entities else state["entity_memory"].get("last_entity"),
            "last_entities": entities,
            "last_task": state.get("intent"),
            "last_result": final_answer
        },
        "messages": [{"role": "assistant", "content": final_answer}]
    }

def synthesizer(state):
    """Generate final response using RAG-based context extraction."""
    resolved = state.get("resolved_query", state.get("user_query", ""))
    intent = state.get("intent", "summarize")
    entity_memory = state.get("entity_memory", {})
    step_outputs = state.get("step_outputs", {})
    
    # Handle out-of-scope queries
    if state.get("replan_decision") == "out_of_scope":
        return _build_response(
            "I'm a news analysis assistant and don't handle prediction questions like stock prices or investment advice. I can help with news summaries, sentiment analysis, entity comparisons, and timelines. Try that?",
            state
        )
    
    # Handle empty results
    all_empty = all(
        output.get("status") == "empty" 
        for output in step_outputs.values()
    ) if step_outputs else True
    
    if all_empty:
        return _build_response(
            "I wasn't able to find news articles about this query. Try rephrasing.",
            state
        )
    
    last_result = entity_memory.get("last_result", "")
    
    # Check for new information requests
    new_info_patterns = [
        r'what about', r'how about', r'connection', r'stance', 
        r'position', r'view', r'opinion', r'relation'
    ]
    is_new_info_request = any(
        re.search(pattern, state.get("user_query", "").lower())
        for pattern in new_info_patterns
    )
    
    # Use prior result if it covers the query and it's not a new info request
    if (last_result and not is_new_info_request 
        and _prior_covers_query(resolved, last_result)):
        prior_prompt = f"Answer this question using only the prior result below.\nQuestion: {resolved}\nPrior result: {last_result}\nGive a direct, concise answer."
        return _build_response(_analyze_with_best_model(prior_prompt), state)
    
    # Build response from fresh results using RAG
    combined = extract_relevant_chunks(step_outputs, resolved, max_tokens=2000)
    
    # Add prior context if available
    prior_context = ""
    for prior_entity in state.get("prior_entity_results", []):
        prior_context += f"- {prior_entity['entity']}: {prior_entity['result'][:500]}\n"
    
    if prior_context:
        combined += f"\n\nPrevious context:\n{prior_context}"
    
    prompt = f"Original query: {resolved}\n\nResearch outputs:\n{combined}\n\nWrite a clear, structured answer. Be concise but informative."
    
    return _build_response(_analyze_with_best_model(prompt), state)