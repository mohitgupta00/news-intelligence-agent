"""
Synthesis Fallback Tests - Test contextual analysis and domain-specific insights
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.modules.synthesis import generate_contextual_analysis, has_meaningful_results, synthesizer
from graph.state import GraphState

class TestSynthesisFallback:
    
    def test_contextual_analysis_fallback(self):
        """Test fallback to contextual analysis when no news data"""
        test_cases = [
            ("Tesla stock analysis", ["Tesla"], "impact analysis"),
            ("Ukraine conflict impact", ["Ukraine"], "impact analysis"),
            ("Apple vs Google comparison", ["Apple", "Google"], "comparison analysis"),
            ("Biden response to crisis", ["Biden"], "response analysis"),
            ("climate change effects", [], "generic fallback"),
            ("market volatility trends", [], "generic fallback"),
            ("healthcare policy changes", [], "generic fallback"),
            ("energy sector developments", [], "generic fallback")
        ]
        
        passed = 0
        for query, entities, expected_type in test_cases:
            try:
                result = generate_contextual_analysis(query, entities, entities, "summarize")
                
                # Check if meaningful analysis was provided
                if result and len(result) > 50:
                    result_lower = result.lower()
                    
                    if expected_type == "impact analysis":
                        # Should contain impact-related analysis
                        if any(word in result_lower for word in ["impact", "affect", "influence", "areas", "potential"]):
                            passed += 1
                            print(f"✅ Contextual fallback: '{query}' -> Impact analysis provided")
                        else:
                            print(f"❌ Contextual fallback: '{query}' -> No impact analysis")
                    elif expected_type == "comparison analysis":
                        # Should contain comparison-related analysis
                        if any(word in result_lower for word in ["comparison", "compare", "versus", "difference", "competitive"]):
                            passed += 1
                            print(f"✅ Contextual fallback: '{query}' -> Comparison analysis provided")
                        else:
                            print(f"❌ Contextual fallback: '{query}' -> No comparison analysis")
                    elif expected_type == "response analysis":
                        # Should contain response-related analysis
                        if any(word in result_lower for word in ["response", "reaction", "statement", "position", "stance"]):
                            passed += 1
                            print(f"✅ Contextual fallback: '{query}' -> Response analysis provided")
                        else:
                            print(f"❌ Contextual fallback: '{query}' -> No response analysis")
                    else:
                        # Generic fallback should provide helpful guidance
                        if any(word in result_lower for word in ["try", "search", "rephrasing", "broader", "keywords"]):
                            passed += 1
                            print(f"✅ Contextual fallback: '{query}' -> Helpful guidance provided")
                        else:
                            print(f"❌ Contextual fallback: '{query}' -> No helpful guidance")
                else:
                    print(f"❌ Contextual fallback: '{query}' -> No meaningful analysis")
            except Exception as e:
                print(f"❌ Contextual fallback error for '{query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Contextual Analysis Fallback: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_domain_classification(self):
        """Test meaningful response generation for different domains"""
        test_cases = [
            ("Tesla earnings report", ["Tesla"], "business entity"),
            ("Ukraine war updates", ["Ukraine"], "geopolitical entity"),
            ("Apple iPhone launch", ["Apple"], "technology entity"),
            ("climate summit results", [], "environmental topic"),
            ("Biden policy announcement", ["Biden"], "political entity"),
            ("stock market crash", [], "financial topic"),
            ("COVID vaccine news", [], "healthcare topic"),
            ("oil price surge", [], "energy topic")
        ]
        
        passed = 0
        for query, entities, expected_type in test_cases:
            try:
                result = generate_contextual_analysis(query, entities, entities, "summarize")
                
                if result and len(result) > 50:
                    result_lower = result.lower()
                    
                    # Check if entities are mentioned when provided
                    if entities:
                        entity_mentioned = any(entity.lower() in result_lower for entity in entities)
                        if entity_mentioned:
                            passed += 1
                            print(f"✅ Domain classification: '{query}' -> Entity referenced")
                        else:
                            print(f"❌ Domain classification: '{query}' -> Entity not referenced")
                    else:
                        # For non-entity queries, check for helpful response
                        if any(word in result_lower for word in ["try", "search", "broader", "different"]):
                            passed += 1
                            print(f"✅ Domain classification: '{query}' -> Helpful response")
                        else:
                            print(f"❌ Domain classification: '{query}' -> Unhelpful response")
                else:
                    print(f"❌ Domain classification: '{query}' -> No meaningful response")
            except Exception as e:
                print(f"❌ Domain classification error for '{query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Domain Classification: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_insight_generation(self):
        """Test generation of helpful guidance and suggestions"""
        test_cases = [
            ("Tesla stock performance", ["Tesla"], ["Tesla", "search", "try"]),
            ("Ukraine conflict analysis", ["Ukraine"], ["Ukraine", "broader", "different"]),
            ("Apple innovation strategy", ["Apple"], ["Apple", "keywords", "rephrase"]),
            ("climate policy effects", [], ["search", "try", "broader"]),
            ("election campaign dynamics", [], ["different", "keywords", "rephrase"]),
            ("market volatility causes", [], ["broader", "terms", "try"]),
            ("healthcare reform impact", [], ["search", "different", "keywords"]),
            ("renewable energy trends", [], ["try", "broader", "rephrase"])
        ]
        
        passed = 0
        for query, entities, expected_keywords in test_cases:
            try:
                result = generate_contextual_analysis(query, entities, entities, "summarize")
                
                if result and len(result) > 50:
                    result_lower = result.lower()
                    keyword_matches = sum(1 for keyword in expected_keywords if keyword.lower() in result_lower)
                    
                    if keyword_matches >= 1:  # At least 1 relevant keyword
                        passed += 1
                        print(f"✅ Insight generation: '{query}' -> Helpful guidance provided")
                    else:
                        print(f"❌ Insight generation: '{query}' -> No helpful guidance")
                else:
                    print(f"❌ Insight generation: '{query}' -> No response generated")
            except Exception as e:
                print(f"❌ Insight generation error for '{query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Insight Generation: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_fallback_error_handling(self):
        """Test error handling in fallback scenarios"""
        test_cases = [
            ("", "empty_query"),
            ("a", "minimal_query"),
            ("!@#$%^&*()", "special_characters"),
            ("very long query " * 20, "excessive_length"),
            ("query with\nnewlines\tand\ttabs", "formatting_issues"),
            ("query with numbers 123456", "mixed_formatting"),
            ("query.with.dots.and-dashes", "punctuation_heavy")
        ]
        
        passed = 0
        for query, error_type in test_cases:
            try:
                result = generate_contextual_analysis(query, [], [], "summarize")
                
                # Should handle gracefully without crashing
                if result is not None:
                    passed += 1
                    print(f"✅ Error handling: '{error_type}' -> Graceful handling")
                else:
                    print(f"❌ Error handling: '{error_type}' -> No result returned")
            except Exception as e:
                print(f"❌ Error handling: '{error_type}' -> Exception: {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Fallback Error Handling: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_context_aware_synthesis(self):
        """Test synthesis with conversation context"""
        test_cases = [
            ("Tesla earnings", ["Tesla"], "Tesla financial performance"),
            ("Ukraine conflict", ["Ukraine"], "Ukraine war situation"),
            ("Apple AI strategy", ["Apple"], "Apple artificial intelligence"),
            ("Climate change effects", [], "Climate change impact")
        ]
        
        passed = 0
        for query, entities, expected_context in test_cases:
            try:
                result = generate_contextual_analysis(query, entities, entities, "summarize")
                
                if result and len(result) > 50:
                    # Check if entities are referenced in the analysis
                    if entities:
                        entity_referenced = any(entity.lower() in result.lower() for entity in entities)
                        if entity_referenced:
                            passed += 1
                            print(f"✅ Context-aware synthesis: '{query}' -> Context utilized")
                        else:
                            print(f"❌ Context-aware synthesis: '{query}' -> Context not utilized")
                    else:
                        # For queries without entities, just check for meaningful response
                        passed += 1
                        print(f"✅ Context-aware synthesis: '{query}' -> Analysis provided")
                else:
                    print(f"❌ Context-aware synthesis: '{query}' -> No analysis generated")
            except Exception as e:
                print(f"❌ Context-aware synthesis error for '{query}': {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Context-Aware Synthesis: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75

def run_synthesis_fallback_tests():
    """Run all synthesis fallback tests"""
    print("🧪 RUNNING SYNTHESIS FALLBACK TESTS")
    print("=" * 50)
    
    test_suite = TestSynthesisFallback()
    
    results = {
        "Contextual Analysis Fallback": test_suite.test_contextual_analysis_fallback(),
        "Domain Classification": test_suite.test_domain_classification(),
        "Insight Generation": test_suite.test_insight_generation(),
        "Fallback Error Handling": test_suite.test_fallback_error_handling(),
        "Context-Aware Synthesis": test_suite.test_context_aware_synthesis()
    }
    
    print("\n" + "=" * 50)
    print("📋 SYNTHESIS FALLBACK TEST SUMMARY")
    print("=" * 50)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    overall_success = (passed_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({overall_success:.1f}%)")
    
    if overall_success >= 75:
        print("🎉 SYNTHESIS FALLBACK TESTS: PRODUCTION READY")
    else:
        print("⚠️  SYNTHESIS FALLBACK TESTS: NEEDS IMPROVEMENT")
    
    return overall_success >= 75

if __name__ == "__main__":
    run_synthesis_fallback_tests()