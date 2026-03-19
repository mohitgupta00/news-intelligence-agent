"""Synthesis node: final response generation with RAG-based context extraction."""

import re
from tools.analyze_text import _analyze_with_best_model
from utils.text_processing import extract_relevant_chunks

def _prior_covers_query(query, last_result, threshold=0.90):
    """Check if prior result covers current query using similarity."""
    if not last_result or not query:
        return False
    
    # Entity-specific validation
    query_lower = query.lower()
    result_lower = last_result.lower()
    
    # Extract key entities from both
    important_entities = ["trump", "biden", "israel", "iran", "tesla", "apple", "google", "microsoft"]
    query_entities = [e for e in important_entities if e in query_lower]
    result_entities = [e for e in important_entities if e in result_lower]
    
    # If query has specific entities not in result, don't reuse
    if query_entities and not any(e in result_entities for e in query_entities):
        return False
    
    # Stricter similarity threshold
    try:
        from utils.text_processing import get_embedder, cosine_similarity
        embedder = get_embedder()
        if embedder:
            embeddings = embedder.encode([query, last_result[:400]])
            return cosine_similarity(embeddings[0], embeddings[1]) >= threshold
    except:
        pass
    
    # More conservative keyword fallback
    def tokenize(text):
        return set(re.findall(r'\b\w{4,}\b', text.lower()))
    
    query_tokens = tokenize(query)
    result_tokens = tokenize(last_result[:400])
    
    if not query_tokens:
        return False
    
    overlap = len(query_tokens & result_tokens)
    return overlap / len(query_tokens) >= 0.70  # Much stricter

def generate_contextual_analysis(query: str, context_entities: list, active_entities: list, intent: str) -> str:
    """Generate contextual analysis when direct search results are unavailable."""
    
    # Extract key components from query
    query_lower = query.lower()
    all_entities = list(set(context_entities + active_entities))
    
    # Identify query type and provide contextual insights
    if any(word in query_lower for word in ['impact', 'affect', 'influence', 'consequence']):
        # Impact analysis
        if len(all_entities) >= 2:
            primary_entity = all_entities[0]
            secondary_entity = all_entities[1]
            
            # Generate logical impact analysis
            impact_areas = {
                'economic': ['trade', 'market', 'economy', 'business', 'financial'],
                'diplomatic': ['relations', 'policy', 'government', 'alliance', 'treaty'],
                'technological': ['innovation', 'development', 'research', 'ai', 'tech'],
                'geopolitical': ['security', 'military', 'defense', 'conflict', 'war']
            }
            
            relevant_areas = []
            for area, keywords in impact_areas.items():
                if any(keyword in query_lower for keyword in keywords):
                    relevant_areas.append(area)
            
            if not relevant_areas:
                relevant_areas = ['economic', 'diplomatic']  # Default areas
            
            analysis = f"While I don't have specific recent news about {query}, I can provide contextual analysis:\n\n"
            analysis += f"**Potential {primary_entity}-{secondary_entity} Impact Areas:**\n"
            
            for area in relevant_areas[:2]:  # Limit to 2 areas
                if area == 'economic':
                    analysis += f"• **Economic**: Trade relationships, market dynamics, and business partnerships could be affected\n"
                elif area == 'diplomatic':
                    analysis += f"• **Diplomatic**: Government relations and policy coordination may see changes\n"
                elif area == 'technological':
                    analysis += f"• **Technological**: Innovation partnerships and tech development could be influenced\n"
                elif area == 'geopolitical':
                    analysis += f"• **Geopolitical**: Security considerations and strategic alignments may shift\n"
            
            analysis += f"\n*Note: This analysis is based on general relationship patterns. For specific recent developments, try searching for broader terms like '{primary_entity} {secondary_entity}' or '{primary_entity} news'.*"
            return analysis
    
    elif any(word in query_lower for word in ['response', 'reaction', 'stance', 'position']):
        # Response/reaction analysis
        if all_entities:
            entity = all_entities[0]
            analysis = f"While I don't have specific recent statements from {entity} about this topic, typical response patterns might include:\n\n"
            analysis += f"• **Official statements** through government channels or corporate communications\n"
            analysis += f"• **Policy adjustments** or strategic positioning changes\n"
            analysis += f"• **Stakeholder engagement** and public messaging\n\n"
            analysis += f"*For the most current {entity} response, try searching for '{entity} statement' or '{entity} official response'.*"
            return analysis
    
    elif any(word in query_lower for word in ['compare', 'comparison', 'versus', 'vs', 'difference']):
        # Comparison analysis
        if len(all_entities) >= 2:
            entity1, entity2 = all_entities[0], all_entities[1]
            analysis = f"While I don't have recent comparative news about {entity1} vs {entity2}, here are typical comparison dimensions:\n\n"
            analysis += f"• **Market position** and competitive strategies\n"
            analysis += f"• **Innovation approaches** and technological focus\n"
            analysis += f"• **Business models** and operational differences\n\n"
            analysis += f"*For current comparative analysis, try searching for '{entity1} {entity2} comparison' or individual searches for each entity.*"
            return analysis
    
    # Generic contextual fallback
    if all_entities:
        entities_str = ', '.join(all_entities[:3])
        analysis = f"I couldn't find specific recent news for your query about {entities_str}. "
        analysis += f"This could be because:\n\n"
        analysis += f"• The topic is very recent and hasn't been widely covered yet\n"
        analysis += f"• The specific angle you're asking about may need broader search terms\n"
        analysis += f"• The entities mentioned may not be directly connected in recent news\n\n"
        analysis += f"**Suggestions:**\n"
        analysis += f"• Try broader searches like '{all_entities[0]} news' or '{all_entities[0]} updates'\n"
        if len(all_entities) > 1:
            analysis += f"• Search for individual entities separately: '{all_entities[0]}' and '{all_entities[1]}'\n"
        analysis += f"• Use different keywords or rephrase your question\n"
        return analysis
    
    # Final fallback
    return "I wasn't able to find recent news articles for this specific query. Try rephrasing with different keywords or broader terms, and I'll search again."

def has_meaningful_results(step_outputs: dict) -> bool:
    """Check if step outputs contain meaningful results beyond basic failures."""
    if not step_outputs:
        return False
    
    for output in step_outputs.values():
        result = output.get('result', '')
        status = output.get('status', '')
        
        # Check for meaningful content
        if (status == 'success' and result and 
            len(result.strip()) > 100 and 
            not any(phrase in result.lower() for phrase in [
                'no recent news', 'no articles found', 'try a different search',
                'no information found', 'please try again'
            ])):
            return True
    
    return False
def extract_entities_from_query(query: str) -> list:
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
    
    # Check if all step outputs are empty or failed
    all_empty = all(
        output.get('status') == 'empty' or not output.get('result', '').strip()
        for output in step_outputs.values()
    ) if step_outputs else True
    
    # Handle empty results with contextual analysis
    if all_empty or not has_meaningful_results(step_outputs):
        # Get available context for analysis
        context_entities = entity_memory.get('last_entities', [])
        active_entities = state.get('active_entities', [])
        extracted_entities = state.get('extracted_entities', [])
        
        # Combine all available entities
        all_available_entities = list(set(context_entities + active_entities + extracted_entities))
        
        # Generate contextual analysis instead of generic "not found" message
        contextual_response = generate_contextual_analysis(
            resolved, 
            context_entities, 
            all_available_entities, 
            intent
        )
        
        return _build_response(contextual_response, state)
    
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