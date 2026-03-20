#!/usr/bin/env python3
"""Debug search variants generation."""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def extract_keywords(query: str):
    """Extract meaningful keywords from query."""
    # Remove common stop words and extract meaningful terms
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'about', 'how', 'what', 'when', 'where', 'why'}
    words = re.findall(r'\\b\\w{3,}\\b', query.lower())
    return [w for w in words if w not in stop_words][:4]  # Max 4 keywords

def extract_main_entities(query: str) -> str:
    """Extract main entities for broad search."""
    entity_patterns = {
        'countries': ['israel', 'iran', 'india', 'china', 'usa', 'russia', 'ukraine', 'germany', 'france', 'uk'],
        'companies': ['apple', 'google', 'microsoft', 'tesla', 'amazon', 'meta', 'nvidia', 'openai'],
        'people': ['trump', 'biden', 'putin', 'xi', 'musk', 'bezos', 'gates']
    }
    
    query_lower = query.lower()
    found_entities = []
    
    for category, entities in entity_patterns.items():
        for entity in entities:
            if entity in query_lower:
                found_entities.append(entity.title())
    
    return ' '.join(found_entities[:2]) if found_entities else ' '.join(extract_keywords(query)[:2])

def generate_search_variants(query: str):
    """Generate multiple search variants for triangulation."""
    print(f"Generating variants for: '{query}'")
    
    variants = [query]  # Original query first
    print(f"  Variant 1 (original): '{query}'")
    
    # Extract components
    keywords = extract_keywords(query)
    entities = extract_main_entities(query)
    
    print(f"  Keywords: {keywords}")
    print(f"  Entities: '{entities}'")
    
    # Variant 2: Main entities only (broader search)
    if entities and entities.strip() != query.strip():
        variants.append(entities)
        print(f"  Variant 2 (entities): '{entities}'")
    
    # Variant 3: Keywords combination
    if len(keywords) >= 2:
        keyword_combo = ' '.join(keywords[:3])
        variants.append(keyword_combo)
        print(f"  Variant 3 (keywords): '{keyword_combo}'")
    
    # Variant 4: Topic-focused (remove specific constraints)
    topic_query = re.sub(r'\\b(latest|recent|today|yesterday|this\\s+week)\\b', '', query, flags=re.IGNORECASE).strip()
    if topic_query and topic_query != query:
        variants.append(topic_query)
        print(f"  Variant 4 (topic): '{topic_query}'")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in variants:
        v_clean = v.strip()
        if v_clean and v_clean not in seen and len(v_clean) > 2:
            seen.add(v_clean)
            unique_variants.append(v_clean)
    
    final_variants = unique_variants[:3]  # Max 3 variants
    print(f"  Final variants: {final_variants}")
    return final_variants

def test_search_variants():
    """Test search variants generation."""
    
    test_queries = [
        "Israel Iran war news",
        "Israel Iran war latest news", 
        "latest updates on israel iran war"
    ]
    
    for query in test_queries:
        print(f"\\nTesting: '{query}'")
        print("=" * 50)
        variants = generate_search_variants(query)
        print()

if __name__ == "__main__":
    test_search_variants()