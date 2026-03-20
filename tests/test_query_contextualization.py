"""
Query Contextualization Tests - Test pronoun resolution, context switching, and fallback strategies.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.modules.query_processing import resolve_contextual_query

class TestQueryContextualization:
    """Test suite for query contextualization logic"""
    
    def test_pronoun_resolution(self):
        """Test pronoun and reference resolution"""
        
        conversation_scenarios = [
            # Scenario 1: War context
            [
                ("Israel Iran conflict", "Israel Iran conflict"),
                ("How is this affecting India?", "How is Israel Iran conflict affecting India?"),
                ("What about their economies?", "What about Israel Iran economies?"),
            ],
            
            # Scenario 2: Company context
            [
                ("Apple earnings report", "Apple earnings report"),
                ("What about their competition?", "What about Apple competition?"),
                ("Any updates on it?", "Any updates on Apple?"),
            ],
            
            # Scenario 3: Multi-entity context
            [
                ("Tesla vs Ford electric vehicles", "Tesla vs Ford electric vehicles"),
                ("How are they performing?", "How are Tesla Ford performing?"),
                ("Latest on their rivalry?", "Latest on Tesla Ford rivalry?"),
            ]
        ]
        
        results = []
        
        for scenario_idx, scenario in enumerate(conversation_scenarios):
            print(f"\n--- Scenario {scenario_idx + 1} ---")
            
            # Simulate conversation state
            active_entities = []
            last_topic = ""
            
            for turn_idx, (user_query, expected_resolved) in enumerate(scenario):
                # Build conversation state
                conversation_state = {
                    'active_entities': active_entities,
                    'last_topic': last_topic,
                    'conversation_history': [q for q, _ in scenario[:turn_idx]]
                }
                
                try:
                    # Match the actual function signature
                    entity_memory = {
                        'last_entities': active_entities,
                        'last_task': last_topic
                    }
                    conversation_history = [{'query': q} for q, _ in scenario[:turn_idx]]
                    
                    resolved_query = resolve_contextual_query(user_query, entity_memory, conversation_history)
                    
                    # Update state for next turn
                    if turn_idx == 0:  # First query establishes context
                        if "Israel Iran" in user_query:
                            active_entities = ["Israel", "Iran"]
                            last_topic = "conflict"
                        elif "Apple" in user_query:
                            active_entities = ["Apple"]
                            last_topic = "earnings"
                        elif "Tesla" in user_query and "Ford" in user_query:
                            active_entities = ["Tesla", "Ford"]
                            last_topic = "electric vehicles"
                    
                    # Check resolution quality
                    success = self._evaluate_resolution(user_query, resolved_query, expected_resolved, active_entities)
                    
                    results.append({
                        'scenario': scenario_idx + 1,
                        'turn': turn_idx + 1,
                        'user_query': user_query,
                        'expected': expected_resolved,
                        'resolved': resolved_query,
                        'success': success
                    })
                    
                    status = "✅" if success else "❌"
                    print(f"{status} Turn {turn_idx + 1}: '{user_query}' -> '{resolved_query}'")
                    
                except Exception as e:
                    results.append({
                        'scenario': scenario_idx + 1,
                        'turn': turn_idx + 1,
                        'user_query': user_query,
                        'expected': expected_resolved,
                        'error': str(e),
                        'success': False
                    })
                    print(f"❌ Turn {turn_idx + 1}: '{user_query}' -> ERROR: {str(e)[:50]}")
        
        # Analyze results
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        
        print(f"\n=== PRONOUN RESOLUTION ANALYSIS ===")
        print(f"Overall Success: {successful}/{total} ({successful/total*100:.1f}%)")
        
        # Should handle at least 70% of pronoun resolution cases
        assert successful / total >= 0.7, f"Pronoun resolution too low: {successful/total:.2f} < 0.7"
    
    def test_context_switching(self):
        """Test topic switching scenarios"""
        
        conversation_scenarios = [
            [
                ("Apple news", "Apple news"),
                ("Now tell me about Google", "Google news"),  # Context should switch
                ("What about their AI?", "What about Google AI?"),  # Should use new context
            ],
            [
                ("Tesla stock performance", "Tesla stock performance"),
                ("Switch to Microsoft", "Microsoft news"),  # Explicit switch
                ("How are they doing?", "How are Microsoft doing?"),  # New context
            ]
        ]
        
        results = []
        
        for scenario_idx, scenario in enumerate(conversation_scenarios):
            print(f"\n--- Context Switch Scenario {scenario_idx + 1} ---")
            
            active_entities = []
            last_topic = ""
            
            for turn_idx, (user_query, expected_resolved) in enumerate(scenario):
                conversation_state = {
                    'active_entities': active_entities,
                    'last_topic': last_topic,
                    'conversation_history': [q for q, _ in scenario[:turn_idx]]
                }
                
                try:
                    entity_memory = {
                        'last_entities': active_entities,
                        'last_task': last_topic
                    }
                    conversation_history = [{'query': q} for q, _ in scenario[:turn_idx]]
                    
                    resolved_query = resolve_contextual_query(user_query, entity_memory, conversation_history)
                    
                    # Update context based on explicit switches
                    if "Google" in user_query and turn_idx == 1:
                        active_entities = ["Google"]
                        last_topic = "news"
                    elif "Microsoft" in user_query and turn_idx == 1:
                        active_entities = ["Microsoft"]
                        last_topic = "news"
                    elif turn_idx == 0:
                        if "Apple" in user_query:
                            active_entities = ["Apple"]
                            last_topic = "news"
                        elif "Tesla" in user_query:
                            active_entities = ["Tesla"]
                            last_topic = "stock"
                    
                    success = self._evaluate_resolution(user_query, resolved_query, expected_resolved, active_entities)
                    
                    results.append({
                        'scenario': scenario_idx + 1,
                        'turn': turn_idx + 1,
                        'user_query': user_query,
                        'expected': expected_resolved,
                        'resolved': resolved_query,
                        'success': success
                    })
                    
                    status = "✅" if success else "❌"
                    print(f"{status} Turn {turn_idx + 1}: '{user_query}' -> '{resolved_query}'")
                    
                except Exception as e:
                    results.append({
                        'scenario': scenario_idx + 1,
                        'turn': turn_idx + 1,
                        'user_query': user_query,
                        'error': str(e),
                        'success': False
                    })
                    print(f"❌ Turn {turn_idx + 1}: ERROR: {str(e)[:50]}")
        
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        
        print(f"\n=== CONTEXT SWITCHING ANALYSIS ===")
        print(f"Success Rate: {successful}/{total} ({successful/total*100:.1f}%)")
        
        assert successful / total >= 0.6, f"Context switching too low: {successful/total:.2f} < 0.6"
    
    def test_ambiguous_references(self):
        """Test handling of unclear references"""
        
        test_cases = [
            ("What about it?", [], "What about it?"),  # No context - unchanged
            ("How are they doing?", [], "How are they doing?"),  # Empty context - unchanged
            ("This situation is complex", ["Apple", "Google"], "Apple Google situation is complex"),
            ("Any updates?", ["Tesla"], "Any Tesla updates?"),
            ("What's the latest?", ["Biden"], "What's the latest Biden?"),
            ("Tell me more", [], "Tell me more"),  # No context available
        ]
        
        results = []
        
        print(f"\n=== AMBIGUOUS REFERENCE TESTS ===")
        
        for user_query, entities, expected in test_cases:
            conversation_state = {
                'active_entities': entities,
                'last_topic': 'news' if entities else '',
                'conversation_history': []
            }
            
            try:
                resolved_query = resolve_contextual_query(user_query, conversation_state)
                
                # For ambiguous references, check if resolution is reasonable
                if not entities:
                    # No context - should remain unchanged or get helpful fallback
                    success = resolved_query == user_query or "more specific" in resolved_query.lower()
                else:
                    # Has context - should incorporate entities
                    success = any(entity.lower() in resolved_query.lower() for entity in entities)
                
                results.append({
                    'query': user_query,
                    'entities': entities,
                    'expected': expected,
                    'resolved': resolved_query,
                    'success': success
                })
                
                status = "✅" if success else "❌"
                print(f"{status} '{user_query}' + {entities} -> '{resolved_query}'")
                
            except Exception as e:
                results.append({
                    'query': user_query,
                    'entities': entities,
                    'error': str(e),
                    'success': False
                })
                print(f"❌ '{user_query}' -> ERROR: {str(e)[:50]}")
        
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        
        print(f"\nAmbiguous Reference Handling: {successful}/{total} ({successful/total*100:.1f}%)")
        
        assert successful / total >= 0.7, f"Ambiguous reference handling too low: {successful/total:.2f} < 0.7"
    
    def test_contextualization_fallbacks(self):
        """Test 5-layer fallback strategy"""
        
        fallback_scenarios = [
            # Rule-based resolution
            ("What about them?", ["Apple", "Google"], "rule_based"),
            ("How are they doing?", ["Tesla"], "rule_based"),
            
            # Entity memory fallback
            ("Any updates?", ["Microsoft"], "entity_memory"),
            ("Latest news?", ["Biden"], "entity_memory"),
            
            # Keyword matching
            ("Tell me more about this", [], "keyword_matching"),
            ("What's happening with that?", [], "keyword_matching"),
            
            # Original query return (last resort)
            ("Hmm", [], "original_query"),
            ("???", [], "original_query"),
        ]
        
        results = []
        
        print(f"\n=== FALLBACK STRATEGY TESTS ===")
        
        for user_query, entities, expected_strategy in fallback_scenarios:
            conversation_state = {
                'active_entities': entities,
                'last_topic': 'news' if entities else '',
                'conversation_history': ['previous query'] if entities else []
            }
            
            try:
                resolved_query = resolve_contextual_query(user_query, conversation_state)
                
                # Determine which fallback strategy was likely used
                if entities and any(entity.lower() in resolved_query.lower() for entity in entities):
                    actual_strategy = "rule_based" if len(entities) > 1 else "entity_memory"
                elif resolved_query != user_query and len(resolved_query) > len(user_query):
                    actual_strategy = "keyword_matching"
                else:
                    actual_strategy = "original_query"
                
                # Success if any reasonable fallback was used
                success = resolved_query != user_query or len(user_query) < 5
                
                results.append({
                    'query': user_query,
                    'entities': entities,
                    'expected_strategy': expected_strategy,
                    'actual_strategy': actual_strategy,
                    'resolved': resolved_query,
                    'success': success
                })
                
                status = "✅" if success else "❌"
                print(f"{status} '{user_query}' -> '{resolved_query}' ({actual_strategy})")
                
            except Exception as e:
                results.append({
                    'query': user_query,
                    'entities': entities,
                    'error': str(e),
                    'success': False
                })
                print(f"❌ '{user_query}' -> ERROR: {str(e)[:50]}")
        
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        
        print(f"\nFallback Strategy Success: {successful}/{total} ({successful/total*100:.1f}%)")
        
        assert successful / total >= 0.6, f"Fallback strategy success too low: {successful/total:.2f} < 0.6"
    
    def _evaluate_resolution(self, user_query, resolved_query, expected_resolved, active_entities):
        """Evaluate quality of query resolution"""
        
        # If query doesn't need resolution, should remain unchanged
        if user_query == expected_resolved:
            return resolved_query == user_query
        
        # Check if expected entities are incorporated
        if active_entities:
            entities_included = any(entity.lower() in resolved_query.lower() for entity in active_entities)
            if not entities_included:
                return False
        
        # Check if resolution is reasonable (not just concatenation)
        if len(resolved_query) > len(user_query) * 3:  # Too verbose
            return False
        
        # Check if resolution maintains query intent
        key_words = ['what', 'how', 'when', 'where', 'why', 'who']
        user_intent = any(word in user_query.lower() for word in key_words)
        resolved_intent = any(word in resolved_query.lower() for word in key_words)
        
        if user_intent and not resolved_intent:
            return False
        
        return True

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])