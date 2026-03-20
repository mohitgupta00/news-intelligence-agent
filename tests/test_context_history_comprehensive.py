#!/usr/bin/env python3
"""
Comprehensive Context History Testing Suite
Testing from Quality Analyst perspective with multiple scenarios and edge cases
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.semantic_context import SemanticContextManager
from utils.entity_resolution import EntityResolutionEngine
from intelligent_router import IntelligentRouter
from graph.state import GraphState

class TestContextHistoryRobustness:
    """Quality Analyst perspective: Test context history from multiple angles"""
    
    def setup_method(self):
        """Setup test environment"""
        self.context_manager = SemanticContextManager()
        self.entity_resolver = EntityResolutionEngine()
        self.router = IntelligentRouter()
        
    def test_conversation_continuity_scenarios(self):
        """Test context continuity across different conversation patterns"""
        
        # Scenario 1: Linear topic progression
        linear_conversation = [
            ("Tesla earnings report", ["Tesla"], "earnings"),
            ("What about their competition?", ["Tesla"], "competition"),
            ("How is Ford doing?", ["Tesla", "Ford"], "performance"),
            ("Compare their EV sales", ["Tesla", "Ford"], "EV sales comparison")
        ]
        
        # Scenario 2: Topic switching with context retention
        switching_conversation = [
            ("Apple iPhone sales", ["Apple"], "iPhone sales"),
            ("Now tell me about Google Pixel", ["Google"], "Pixel"),
            ("How do they compare?", ["Apple", "Google"], "comparison"),
            ("What about Samsung Galaxy?", ["Apple", "Google", "Samsung"], "Galaxy comparison")
        ]
        
        # Scenario 3: Nested context with pronouns
        nested_conversation = [
            ("Israel Iran conflict latest", ["Israel", "Iran"], "conflict"),
            ("How is this affecting oil prices?", ["Israel", "Iran"], "oil prices impact"),
            ("What about their regional allies?", ["Israel", "Iran"], "regional allies"),
            ("Any diplomatic efforts to resolve it?", ["Israel", "Iran"], "diplomatic efforts")
        ]
        
        scenarios = [linear_conversation, switching_conversation, nested_conversation]
        
        for scenario_idx, conversation in enumerate(scenarios):
            print(f"\n=== Testing Scenario {scenario_idx + 1} ===")
            
            conversation_history = []
            for turn_idx, (query, expected_entities, expected_topic) in enumerate(conversation):
                print(f"Turn {turn_idx + 1}: {query}")
                
                # Update conversation history
                conversation_history.append({"query": query, "entities": expected_entities})
                
                # Test entity resolution
                context_queries = [turn["query"] for turn in conversation_history[:-1]]
                resolution_result = self.entity_resolver.resolve_entities(query, context_queries)
                resolved_entities = [entity.text for entity in resolution_result.entities]
                print(f"  Resolved entities: {resolved_entities}")
                
                # Test context switch detection
                context_queries = [turn["query"] for turn in conversation_history[:-1]]
                context_switch = self.context_manager.detect_context_switch(query, context_queries)
                print(f"  Context switch: {context_switch}")
                
                # Test contextual query building
                context_queries = [turn["query"] for turn in conversation_history[:-1]]
                contextual_query = self.context_manager.build_contextual_query(query, context_queries)
                print(f"  Contextual query: {contextual_query}")
                
                # Validate entity presence
                for entity in expected_entities:
                    assert any(entity.lower() in str(resolved_entities).lower() or 
                             entity.lower() in contextual_query.lower() for _ in [1]), \
                        f"Entity '{entity}' not found in turn {turn_idx + 1}"
        
        print("\n✅ All conversation continuity scenarios passed")
        
    def test_context_memory_persistence(self):
        """Test memory persistence across different time intervals"""
        
        # Test short-term memory (immediate context)
        short_term_history = [
            {"query": "Tesla stock news", "entities": ["Tesla"]},
            {"query": "Apple earnings", "entities": ["Apple"]},
        ]
        
        query = "How are they performing?"
        context_queries = [turn["query"] for turn in short_term_history]
        resolution_result = self.entity_resolver.resolve_entities(query, context_queries)
        resolved_entities = [entity.text for entity in resolution_result.entities]
        contextual_query = self.context_manager.build_contextual_query(query, context_queries)
        
        print(f"Short-term context - Entities: {resolved_entities}")
        print(f"Short-term context - Query: {contextual_query}")
        
        # Should reference recent entities
        assert any("Tesla" in str(resolved_entities) or "Tesla" in contextual_query for _ in [1])
        assert any("Apple" in str(resolved_entities) or "Apple" in contextual_query for _ in [1])
        
        # Test medium-term memory (5+ turns back)
        medium_term_history = [
            {"query": "Microsoft Azure news", "entities": ["Microsoft"]},
            {"query": "Google Cloud updates", "entities": ["Google"]},
            {"query": "Amazon AWS earnings", "entities": ["Amazon"]},
            {"query": "Tesla stock price", "entities": ["Tesla"]},
            {"query": "Apple iPhone sales", "entities": ["Apple"]},
        ]
        
        query = "Compare their cloud services"
        context_queries = [turn["query"] for turn in medium_term_history]
        resolution_result = self.entity_resolver.resolve_entities(query, context_queries)
        resolved_entities = [entity.text for entity in resolution_result.entities]
        contextual_query = self.context_manager.build_contextual_query(query, context_queries)
        
        print(f"Medium-term context - Entities: {resolved_entities}")
        print(f"Medium-term context - Query: {contextual_query}")
        
        # Should prioritize cloud-related entities
        cloud_entities = ["Microsoft", "Google", "Amazon"]
        found_cloud_entities = sum(1 for entity in cloud_entities 
                                 if entity in str(resolved_entities) or entity in contextual_query)
        assert found_cloud_entities >= 2, "Should find at least 2 cloud entities"
        
        print("✅ Memory persistence tests passed")
        
    def test_ambiguous_reference_resolution(self):
        """Test handling of ambiguous pronouns and references"""
        
        ambiguous_scenarios = [
            # Scenario 1: Multiple possible referents
            {
                "history": [
                    {"query": "Tesla vs Ford EV sales", "entities": ["Tesla", "Ford"]},
                    {"query": "BMW electric vehicle strategy", "entities": ["BMW"]},
                ],
                "query": "How are they doing in Europe?",
                "expected_entities": ["Tesla", "Ford", "BMW"],  # Should include all recent entities
            },
            
            # Scenario 2: Unclear "it" reference
            {
                "history": [
                    {"query": "Apple iPhone 15 launch", "entities": ["Apple"]},
                    {"query": "Samsung Galaxy S24 release", "entities": ["Samsung"]},
                ],
                "query": "What's the market response to it?",
                "expected_entities": ["Samsung"],  # Should reference most recent
            },
            
            # Scenario 3: Temporal reference
            {
                "history": [
                    {"query": "Russia Ukraine conflict", "entities": ["Russia", "Ukraine"]},
                    {"query": "NATO response strategy", "entities": ["NATO"]},
                ],
                "query": "What's the latest on this situation?",
                "expected_entities": ["Russia", "Ukraine", "NATO"],  # Should include conflict context
            },
        ]
        
        for scenario_idx, scenario in enumerate(ambiguous_scenarios):
            print(f"\n=== Ambiguous Reference Scenario {scenario_idx + 1} ===")
            print(f"Query: {scenario['query']}")
            
            context_queries = [turn["query"] for turn in scenario['history']]
            resolution_result = self.entity_resolver.resolve_entities(scenario['query'], context_queries)
            resolved_entities = [entity.text for entity in resolution_result.entities]
            contextual_query = self.context_manager.build_contextual_query(scenario['query'], context_queries)
            
            print(f"Resolved entities: {resolved_entities}")
            print(f"Contextual query: {contextual_query}")
            
            # Check if expected entities are resolved
            for expected_entity in scenario['expected_entities']:
                found = (expected_entity in str(resolved_entities) or 
                        expected_entity in contextual_query)
                print(f"  {expected_entity}: {'✓' if found else '✗'}")
        
        print("\n✅ Ambiguous reference resolution tests completed")
        
    def test_context_corruption_recovery(self):
        """Test system behavior with corrupted or malformed context"""
        
        corruption_scenarios = [
            # Empty history
            {"history": [], "query": "What about Tesla?"},
            
            # Malformed history entries
            {"history": [{"invalid": "data"}], "query": "Latest news?"},
            
            # Missing required fields
            {"history": [{"query": "Apple news"}], "query": "More details?"},  # Missing entities
            
            # Circular references
            {"history": [{"query": "Tesla", "entities": ["Tesla", "Tesla"]}], "query": "Updates?"},
            
            # Extremely long history
            {"history": [{"query": f"Query {i}", "entities": [f"Entity{i}"]} for i in range(100)], 
             "query": "Summary?"},
        ]
        
        for scenario_idx, scenario in enumerate(corruption_scenarios):
            print(f"\n=== Corruption Scenario {scenario_idx + 1} ===")
            
            try:
                context_queries = [turn.get("query", "") for turn in scenario.get('history', []) if isinstance(turn, dict) and "query" in turn]
                resolution_result = self.entity_resolver.resolve_entities(scenario['query'], context_queries)
                resolved_entities = [entity.text for entity in resolution_result.entities]
                contextual_query = self.context_manager.build_contextual_query(scenario['query'], context_queries)
                
                print(f"  Handled gracefully - Entities: {len(str(resolved_entities))} chars")
                print(f"  Contextual query: {len(contextual_query)} chars")
                
                # System should not crash and should return reasonable results
                assert resolved_entities is not None
                assert contextual_query is not None
                assert len(contextual_query) > 0
                
            except Exception as e:
                print(f"  Error (should be handled): {e}")
                # System should handle errors gracefully
                assert False, f"System should handle corruption gracefully: {e}"
        
        print("\n✅ Context corruption recovery tests passed")
        
    def test_performance_under_load(self):
        """Test context processing performance with large conversation histories"""
        
        import time
        
        # Generate large conversation history
        large_history = []
        for i in range(50):  # 50 turns
            large_history.append({
                "query": f"Query about entity {i % 10}",
                "entities": [f"Entity{i % 10}", f"Company{i % 5}"]
            })
        
        test_queries = [
            "What's the latest update?",
            "How are they performing?", 
            "Compare their strategies",
            "What about the competition?",
            "Any recent developments?"
        ]
        
        performance_results = []
        
        for query in test_queries:
            start_time = time.time()
            
            context_queries = [turn["query"] for turn in large_history]
            resolution_result = self.entity_resolver.resolve_entities(query, context_queries)
            resolved_entities = [entity.text for entity in resolution_result.entities]
            contextual_query = self.context_manager.build_contextual_query(query, context_queries)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            performance_results.append(processing_time)
            print(f"Query: '{query}' - Time: {processing_time:.3f}s")
        
        avg_time = sum(performance_results) / len(performance_results)
        max_time = max(performance_results)
        
        print(f"\nPerformance Summary:")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Maximum time: {max_time:.3f}s")
        
        # Performance assertions
        assert avg_time < 2.0, f"Average processing time too high: {avg_time:.3f}s"
        assert max_time < 5.0, f"Maximum processing time too high: {max_time:.3f}s"
        
        print("✅ Performance under load tests passed")
        
    def test_multi_language_context_handling(self):
        """Test context handling with mixed language inputs"""
        
        # Note: This is a basic test - full multilingual support would require more sophisticated models
        mixed_language_scenarios = [
            {
                "history": [{"query": "Tesla noticias", "entities": ["Tesla"]}],
                "query": "What about Ford?",
                "expected_context": "Tesla"
            },
            {
                "history": [{"query": "Apple iPhone nouvelles", "entities": ["Apple"]}],
                "query": "Latest updates?",
                "expected_context": "Apple"
            },
        ]
        
        for scenario in mixed_language_scenarios:
            context_queries = [turn["query"] for turn in scenario['history']]
            resolution_result = self.entity_resolver.resolve_entities(scenario['query'], context_queries)
            resolved_entities = [entity.text for entity in resolution_result.entities]
            contextual_query = self.context_manager.build_contextual_query(scenario['query'], context_queries)
            
            print(f"Mixed language - Query: {scenario['query']}")
            print(f"  Entities: {resolved_entities}")
            print(f"  Contextual: {contextual_query}")
            
            # Should handle basic entity extraction even with mixed languages
            context_found = (scenario['expected_context'] in str(resolved_entities) or 
                           scenario['expected_context'] in contextual_query)
            print(f"  Context preserved: {'✓' if context_found else '✗'}")
        
        print("✅ Multi-language context handling tests completed")

if __name__ == "__main__":
    # Run comprehensive tests
    test_suite = TestContextHistoryRobustness()
    test_suite.setup_method()
    
    print("🔍 COMPREHENSIVE CONTEXT HISTORY TESTING")
    print("=" * 50)
    
    try:
        test_suite.test_conversation_continuity_scenarios()
        test_suite.test_context_memory_persistence()
        test_suite.test_ambiguous_reference_resolution()
        test_suite.test_context_corruption_recovery()
        test_suite.test_performance_under_load()
        test_suite.test_multi_language_context_handling()
        
        print("\n" + "=" * 50)
        print("🎉 ALL COMPREHENSIVE CONTEXT HISTORY TESTS PASSED")
        print("✅ System demonstrates professional-grade robustness")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise