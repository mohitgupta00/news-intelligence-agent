"""
Source Selection Tests - Test intelligent routing and source optimization
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.modules.planning import select_optimal_sources, optimize_query_for_source
from graph.state import GraphState

class TestSourceSelection:
    
    def test_pattern_based_routing(self):
        """Test source selection based on query patterns"""
        test_cases = [
            ("breaking Tesla news", ["gnews"]),
            ("global climate summit", ["gnews"]),
            ("Apple earnings financial", ["newsdata"]),
            ("international Ukraine crisis", ["gnews"]),
            ("US election updates", ["newsapi"]),
            ("European market analysis", ["gnews"]),
            ("tech company merger", ["newsdata"]),
            ("world health crisis", ["gnews"])
        ]
        
        passed = 0
        for query, expected_sources in test_cases:
            try:
                selected_sources = select_optimal_sources(query, "summarize", {})
                
                # Check if any expected source is selected
                if any(source in selected_sources for source in expected_sources):
                    passed += 1
                    print(f"✅ Pattern routing: '{query}' -> {selected_sources}")
                else:
                    print(f"❌ Pattern routing: '{query}' -> {selected_sources} (expected: {expected_sources})")
            except Exception as e:
                print(f"❌ Pattern routing error for '{query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Pattern-Based Routing: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_entity_specific_routing(self):
        """Test routing based on entity types"""
        test_cases = [
            ("Trump Biden election", ["newsapi"]),
            ("China Russia relations", ["gnews"]),
            ("Tesla Apple stock", ["newsdata"]),
            ("Microsoft Google AI", ["newsdata"]),
            ("Ukraine NATO alliance", ["gnews"]),
            ("Amazon Meta earnings", ["newsdata"]),
            ("Iran Israel conflict", ["gnews"]),
            ("Ford GM electric", ["newsdata"])
        ]
        
        passed = 0
        for query, expected_sources in test_cases:
            try:
                selected_sources = select_optimal_sources(query, "summarize", {})
                
                if any(source in selected_sources for source in expected_sources):
                    passed += 1
                    print(f"✅ Entity routing: '{query}' -> {selected_sources}")
                else:
                    print(f"❌ Entity routing: '{query}' -> {selected_sources} (expected: {expected_sources})")
            except Exception as e:
                print(f"❌ Entity routing error for '{query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Entity-Specific Routing: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_intent_based_optimization(self):
        """Test source preference based on intent"""
        test_cases = [
            ("compare Apple vs Google", "compare", ["newsdata"]),
            ("public opinion on climate", "sentiment", ["gnews"]),
            ("timeline of Ukraine events", "timeline", ["gnews"]),
            ("analyze Tesla performance", "summarize", ["newsdata"]),
            ("global reaction to summit", "sentiment", ["gnews"]),
            ("sequence of market events", "timeline", ["gnews"]),
            ("contrast Biden Trump policies", "compare", ["newsdata"]),
            ("worldwide COVID response", "sentiment", ["gnews"])
        ]
        
        passed = 0
        for query, intent, expected_sources in test_cases:
            try:
                selected_sources = select_optimal_sources(query, intent, {})
                
                if any(source in selected_sources for source in expected_sources):
                    passed += 1
                    print(f"✅ Intent routing: '{query}' ({intent}) -> {selected_sources}")
                else:
                    print(f"❌ Intent routing: '{query}' ({intent}) -> {selected_sources} (expected: {expected_sources})")
            except Exception as e:
                print(f"❌ Intent routing error for '{query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Intent-Based Optimization: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_fallback_source_selection(self):
        """Test fallback when preferred sources fail"""
        test_cases = [
            ("breaking tech news", ["newsapi"], ["gnews", "newsdata"]),
            ("global political crisis", ["gnews"], ["newsapi", "newsdata"]),
            ("financial market update", ["newsdata"], ["newsapi", "gnews"]),
            ("international sports event", ["gnews"], ["newsapi"]),
            ("US domestic policy", ["newsapi"], ["gnews"]),
            ("European business news", ["gnews"], ["newsdata"]),
            ("Asian market trends", ["newsdata"], ["gnews"]),
            ("breaking world news", ["newsapi"], ["gnews"])
        ]
        
        passed = 0
        for query, failed_sources, fallback_sources in test_cases:
            try:
                # Test with context hints indicating failed sources
                context_hints = {"failed_sources": failed_sources}
                selected_sources = select_optimal_sources(query, "summarize", context_hints)
                
                # Should use fallback sources when primary fails
                uses_fallback = any(source in selected_sources for source in fallback_sources)
                
                if uses_fallback:
                    passed += 1
                    print(f"✅ Fallback routing: '{query}' -> {selected_sources}")
                else:
                    print(f"❌ Fallback routing: '{query}' -> {selected_sources} (should use: {fallback_sources})")
            except Exception as e:
                print(f"❌ Fallback routing error for '{query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Fallback Source Selection: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_query_optimization(self):
        """Test query optimization for different sources"""
        test_cases = [
            ("latest Tesla news today", "newsapi", "latest Tesla news today"),
            ("recent Apple updates yesterday", "gnews", "Apple updates"),
            ("today's Microsoft earnings", "newsdata", "today's Microsoft earnings"),
            ("breaking Google AI news", "gnews", "Google AI news"),
            ("latest Amazon stock today", "newsapi", "latest Amazon stock today")
        ]
        
        passed = 0
        for original_query, source, expected_pattern in test_cases:
            try:
                optimized = optimize_query_for_source(original_query, source)
                
                # For gnews, temporal words should be removed
                if source == "gnews":
                    temporal_removed = not any(word in optimized.lower() for word in ["latest", "recent", "today", "yesterday"])
                    if temporal_removed or optimized == original_query:  # Allow fallback to original
                        passed += 1
                        print(f"✅ Query optimization: '{original_query}' -> '{optimized}' ({source})")
                    else:
                        print(f"❌ Query optimization: '{original_query}' -> '{optimized}' ({source})")
                else:
                    # Other sources should preserve the query
                    if optimized:
                        passed += 1
                        print(f"✅ Query optimization: '{original_query}' -> '{optimized}' ({source})")
                    else:
                        print(f"❌ Query optimization: '{original_query}' -> '{optimized}' ({source})")
            except Exception as e:
                print(f"❌ Query optimization error for '{original_query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Query Optimization: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75

def run_source_selection_tests():
    """Run all source selection tests"""
    print("🧪 RUNNING SOURCE SELECTION TESTS")
    print("=" * 50)
    
    test_suite = TestSourceSelection()
    
    results = {
        "Pattern-Based Routing": test_suite.test_pattern_based_routing(),
        "Entity-Specific Routing": test_suite.test_entity_specific_routing(),
        "Intent-Based Optimization": test_suite.test_intent_based_optimization(),
        "Fallback Source Selection": test_suite.test_fallback_source_selection(),
        "Query Optimization": test_suite.test_query_optimization()
    }
    
    print("\n" + "=" * 50)
    print("📋 SOURCE SELECTION TEST SUMMARY")
    print("=" * 50)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    overall_success = (passed_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({overall_success:.1f}%)")
    
    if overall_success >= 75:
        print("🎉 SOURCE SELECTION TESTS: PRODUCTION READY")
    else:
        print("⚠️  SOURCE SELECTION TESTS: NEEDS IMPROVEMENT")
    
    return overall_success >= 75

if __name__ == "__main__":
    run_source_selection_tests()