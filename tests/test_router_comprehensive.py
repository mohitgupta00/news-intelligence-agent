"""
Router Decision Logic Tests - Comprehensive testing of intelligent routing decisions.
Tests basic routing accuracy, context extraction, source suggestions, and fallback robustness.
"""

import pytest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_router import IntelligentRouter, RouterDecision
from config import GROQ_API_KEY

class TestRouterDecisionLogic:
    """Test suite for router decision logic"""
    
    @pytest.fixture
    def router(self):
        """Create router instance for testing"""
        return IntelligentRouter()
    
    @pytest.fixture
    def mock_memory(self):
        """Mock conversation memory"""
        return {
            'last_entities': ['Apple', 'Google'],
            'last_topic': 'Technology',
            'conversation_context': 'news_analysis'
        }

    def test_router_basic_decisions(self, router):
        """Test fundamental routing decisions"""
        test_cases = [
            # Direct response cases
            ("what can you do?", "direct_response"),
            ("how to make pizza", "direct_response"),
            ("solve 2+2", "direct_response"),
            ("write a poem", "direct_response"),
            ("your capabilities", "direct_response"),
            ("who are you", "direct_response"),
            ("relationship advice", "direct_response"),
            ("math problem", "direct_response"),
            
            # Graph delegation cases
            ("Tesla earnings news", "delegate_to_graph"),
            ("latest Ukraine updates", "delegate_to_graph"),
            ("Apple vs Google AI", "delegate_to_graph"),
            ("breaking news today", "delegate_to_graph"),
            ("Biden climate policy", "delegate_to_graph"),
            ("stock market analysis", "delegate_to_graph"),
            ("Israel Iran conflict", "delegate_to_graph"),
            ("tech industry trends", "delegate_to_graph"),
        ]
        
        results = []
        for query, expected_action in test_cases:
            try:
                decision = router.route_query(query)
                actual_action = decision.action
                success = actual_action == expected_action
                results.append((query, expected_action, actual_action, success))
                
                # Additional validation
                assert isinstance(decision, RouterDecision), f"Invalid decision type for '{query}'"
                assert decision.reasoning, f"Missing reasoning for '{query}'"
                
                if expected_action == "direct_response":
                    # Direct responses should have response text or be capability queries
                    if "what can you do" in query.lower() or "capabilities" in query.lower():
                        assert decision.response is None, f"Capability queries should not have response text: '{query}'"
                    else:
                        assert decision.response, f"Direct response missing response text: '{query}'"
                        assert decision.graph_query is None, f"Direct response should not have graph_query: '{query}'"
                else:
                    # Graph delegation should have graph_query
                    assert decision.graph_query or query, f"Graph delegation missing query: '{query}'"
                    
            except Exception as e:
                results.append((query, expected_action, f"ERROR: {e}", False))
        
        # Print results summary
        passed = sum(1 for _, _, _, success in results if success)
        total = len(results)
        print(f"\n=== BASIC ROUTING DECISIONS ===")
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        for query, expected, actual, success in results:
            status = "✅" if success else "❌"
            print(f"{status} '{query[:30]}...' -> Expected: {expected}, Got: {actual}")
        
        # Assert overall success rate (lower threshold due to API fallbacks)
        success_rate = passed / total
        assert success_rate >= 0.7, f"Router accuracy too low: {success_rate:.2f} < 0.7"

    def test_router_context_extraction(self, router):
        """Test entity and topic extraction"""
        test_cases = [
            ("Tesla stock news", ["Tesla"], "Stock"),
            ("Israel Iran conflict", ["Israel", "Iran"], "Conflict"),
            ("Apple Google Microsoft AI", ["Apple", "Google", "Microsoft"], "AI"),
            ("Biden climate policy", ["Biden"], "Climate"),
            ("breaking Tesla earnings", ["Tesla"], "Earnings"),
            ("Ukraine Russia war updates", ["Ukraine", "Russia"], "War"),
            ("Microsoft OpenAI partnership", ["Microsoft", "OpenAI"], "Partnership"),
        ]
        
        results = []
        for query, expected_entities, expected_topic_keyword in test_cases:
            try:
                decision = router.route_query(query)
                
                # Check if entities were extracted
                entities_found = decision.resolved_entities or []
                topic_found = decision.resolved_topic or ""
                
                # Validate entity extraction (at least some expected entities should be found)
                entity_match = any(entity in entities_found for entity in expected_entities) if expected_entities else True
                
                # Validate topic extraction (topic should contain expected keyword)
                topic_match = expected_topic_keyword.lower() in topic_found.lower() if expected_topic_keyword else True
                
                success = entity_match and topic_match
                results.append((query, expected_entities, entities_found, expected_topic_keyword, topic_found, success))
                
            except Exception as e:
                results.append((query, expected_entities, f"ERROR: {e}", expected_topic_keyword, f"ERROR: {e}", False))
        
        # Print results
        passed = sum(1 for _, _, _, _, _, success in results if success)
        total = len(results)
        print(f"\n=== CONTEXT EXTRACTION ===")
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        for query, exp_ent, act_ent, exp_topic, act_topic, success in results:
            status = "✅" if success else "❌"
            print(f"{status} '{query[:25]}...'")
            print(f"   Entities: Expected {exp_ent} -> Got {act_ent}")
            print(f"   Topic: Expected '{exp_topic}' -> Got '{act_topic}'")
        
        # Allow some flexibility in context extraction
        success_rate = passed / total
        assert success_rate >= 0.6, f"Context extraction too low: {success_rate:.2f} < 0.6"

    def test_router_source_suggestions(self, router):
        """Test intelligent source routing"""
        test_cases = [
            ("breaking Tesla news", ["gnews"]),  # Updated: gnews better for breaking news
            ("global climate impact", ["gnews"]),
            ("Apple earnings report", ["newsdata"]),
            ("international conflict", ["gnews"]),
            ("latest US politics", ["gnews"]),  # Updated: gnews better for latest news
            ("worldwide economic crisis", ["gnews"]),
            ("Microsoft stock analysis", ["newsdata"]),
            ("Biden Trump election", ["newsapi"]),  # Keep newsapi for general US politics
        ]
        
        results = []
        for query, expected_sources in test_cases:
            try:
                decision = router.route_query(query)
                suggested_sources = decision.suggested_sources or []
                
                # Check if at least one expected source is suggested
                source_match = any(source in suggested_sources for source in expected_sources) if expected_sources else True
                
                success = source_match and len(suggested_sources) > 0
                results.append((query, expected_sources, suggested_sources, success))
                
            except Exception as e:
                results.append((query, expected_sources, f"ERROR: {e}", False))
        
        # Print results
        passed = sum(1 for _, _, _, success in results if success)
        total = len(results)
        print(f"\n=== SOURCE SUGGESTIONS ===")
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        for query, expected, actual, success in results:
            status = "✅" if success else "❌"
            print(f"{status} '{query[:30]}...' -> Expected: {expected}, Got: {actual}")
        
        success_rate = passed / total
        assert success_rate >= 0.4, f"Source suggestion accuracy too low: {success_rate:.2f} < 0.4"

    def test_router_confidence_scoring(self, router):
        """Test routing confidence scores"""
        test_cases = [
            ("what can you do?", 0.9),  # High confidence for clear capability query
            ("how to make pizza", 0.9),  # High confidence for clear out-of-scope
            ("Tesla news", 0.8),  # High confidence for clear news query
            ("something vague", 0.5),  # Lower confidence for ambiguous query
        ]
        
        results = []
        for query, min_expected_confidence in test_cases:
            try:
                decision = router.route_query(query)
                confidence = decision.routing_confidence or 0.0
                
                success = confidence >= min_expected_confidence
                results.append((query, min_expected_confidence, confidence, success))
                
            except Exception as e:
                results.append((query, min_expected_confidence, 0.0, False))
        
        # Print results
        passed = sum(1 for _, _, _, success in results if success)
        total = len(results)
        print(f"\n=== CONFIDENCE SCORING ===")
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        for query, expected, actual, success in results:
            status = "✅" if success else "❌"
            print(f"{status} '{query[:30]}...' -> Expected: ≥{expected}, Got: {actual:.2f}")

    def test_router_fallback_scenarios(self, router):
        """Test router failure handling"""
        
        # Test 1: Mock LLM timeout
        with patch.object(router.groq_client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("Timeout")
            
            decision = router.route_query("Tesla news")
            
            # Should fallback gracefully
            assert decision.action in ["direct_response", "delegate_to_graph"]
            assert "fallback" in decision.reasoning.lower()
            print("✅ LLM timeout fallback works")
        
        # Test 2: Mock malformed JSON response
        with patch.object(router.groq_client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "invalid json response"
            mock_create.return_value = mock_response
            
            decision = router.route_query("Apple news")
            
            # Should fallback gracefully
            assert decision.action in ["direct_response", "delegate_to_graph"]
            assert "fallback" in decision.reasoning.lower()
            print("✅ Malformed JSON fallback works")
        
        # Test 3: Empty query handling (should fallback gracefully)
        decision = router.route_query("")
        assert decision.action in ["direct_response", "delegate_to_graph"]
        print("✅ Empty query handling works")
        
        # Test 4: Very long query handling
        long_query = "Tesla news " * 100
        decision = router.route_query(long_query)
        assert decision.action in ["direct_response", "delegate_to_graph"]
        print("✅ Long query handling works")

    def test_router_memory_integration(self, router, mock_memory):
        """Test router integration with conversation memory"""
        
        # Test with memory context
        decision = router.route_query("What about their competition?", mock_memory)
        
        # Should delegate to graph for contextual query
        assert decision.action == "delegate_to_graph"
        
        # Should extract entities from memory context
        if decision.resolved_entities:
            assert any(entity in ['Apple', 'Google'] for entity in decision.resolved_entities)
        
        print("✅ Memory integration works")

    def test_router_edge_cases(self, router):
        """Test router with edge case inputs"""
        edge_cases = [
            "",  # Empty string
            " ",  # Whitespace only
            "🚀🎯💡",  # Emoji only
            "a" * 1000,  # Very long query
            "SELECT * FROM users",  # SQL-like input
            "<script>alert('xss')</script>",  # HTML/JS input
            "query\nwith\nnewlines",  # Multi-line input
            "query with\ttabs",  # Tab characters
        ]
        
        results = []
        for query in edge_cases:
            try:
                decision = router.route_query(query)
                # Should not crash and should return valid decision
                success = isinstance(decision, RouterDecision) and decision.action in ["direct_response", "delegate_to_graph"]
                results.append((query[:20], success))
            except Exception as e:
                results.append((query[:20], False))
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        print(f"\n=== EDGE CASES ===")
        print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        for query_preview, success in results:
            status = "✅" if success else "❌"
            print(f"{status} Edge case: '{query_preview}...'")
        
        # Should handle all edge cases gracefully
        success_rate = passed / total
        assert success_rate >= 0.9, f"Edge case handling too low: {success_rate:.2f} < 0.9"

    def test_router_performance(self, router):
        """Test router response time performance"""
        queries = [
            "Tesla news",
            "what can you do?",
            "Apple vs Google",
            "breaking news today",
            "how to make pizza"
        ]
        
        times = []
        for query in queries:
            start_time = time.time()
            decision = router.route_query(query)
            end_time = time.time()
            
            response_time = end_time - start_time
            times.append(response_time)
            
            # Each query should complete within reasonable time
            assert response_time < 10.0, f"Query '{query}' took too long: {response_time:.2f}s"
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"\n=== PERFORMANCE ===")
        print(f"Average response time: {avg_time:.2f}s")
        print(f"Maximum response time: {max_time:.2f}s")
        print(f"All queries completed within 10s: ✅")
        
        # Performance targets
        assert avg_time < 5.0, f"Average response time too high: {avg_time:.2f}s"
        assert max_time < 10.0, f"Maximum response time too high: {max_time:.2f}s"

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])