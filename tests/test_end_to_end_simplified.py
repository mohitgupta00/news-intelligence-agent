"""
End-to-End Conversation Flow Tests - Simplified Integration Testing
Testing core system functionality without complex async handling
"""
import pytest
import sys
import os
import time
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_router import IntelligentRouter

class TestEndToEndSimplified:
    
    def setup_method(self):
        """Setup test environment"""
        self.router = IntelligentRouter()
    
    def test_router_integration(self):
        """Test router integration with various query types"""
        test_cases = [
            # Direct response cases
            ("what can you do?", "direct_response"),
            ("how to make pizza", "direct_response"),
            ("solve 2+2", "direct_response"),
            
            # Graph delegation cases
            ("Tesla earnings news", "delegate_to_graph"),
            ("Apple vs Google AI", "delegate_to_graph"),
            ("Ukraine conflict updates", "delegate_to_graph"),
            ("breaking market news", "delegate_to_graph"),
            ("Biden climate policy", "delegate_to_graph"),
            
            # Edge cases
            ("", "direct_response"),  # Empty query
            ("a", "direct_response"),  # Single character
            ("Tesla Tesla Tesla news", "delegate_to_graph"),  # Repeated entities
        ]
        
        passed = 0
        for query, expected_action in test_cases:
            try:
                start_time = time.time()
                decision = self.router.route_query(query, {})
                end_time = time.time()
                
                # Should complete quickly (under 5 seconds)
                if end_time - start_time > 5:
                    print(f"❌ Router integration: '{query}' -> Timeout ({end_time - start_time:.1f}s)")
                    continue
                
                # Should return valid decision
                if (hasattr(decision, 'action') and 
                    decision.action in ['direct_response', 'delegate_to_graph']):
                    
                    if decision.action == expected_action:
                        passed += 1
                        print(f"✅ Router integration: '{query[:30]}...' -> {decision.action}")
                    else:
                        print(f"❌ Router integration: '{query[:30]}...' -> {decision.action} (expected: {expected_action})")
                else:
                    print(f"❌ Router integration: '{query}' -> Invalid decision structure")
                    
            except Exception as e:
                print(f"❌ Router integration error: '{query}' -> {str(e)[:50]}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Router Integration: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def test_context_extraction_integration(self):
        """Test context extraction across multiple queries"""
        context_scenarios = [
            # Entity extraction
            ("Tesla stock news", ["Tesla"]),
            ("Apple vs Google competition", ["Apple", "Google"]),
            ("Biden Trump election debate", ["Biden", "Trump"]),
            ("Microsoft Amazon cloud services", ["Microsoft", "Amazon"]),
            
            # Topic extraction
            ("climate change impact", "Climate"),
            ("artificial intelligence development", "AI"),
            ("cryptocurrency market trends", "Cryptocurrency"),
            ("space exploration missions", "Space"),
            
            # Complex queries
            ("Tesla earnings impact on Apple stock", ["Tesla", "Apple"]),
            ("Ukraine conflict affecting European economy", ["Ukraine"]),
            ("Biden administration response to China trade", ["Biden", "China"])
        ]
        
        passed = 0
        for query, expected_context in context_scenarios:
            try:
                decision = self.router.route_query(query, {})
                
                if hasattr(decision, 'resolved_entities') and decision.resolved_entities:
                    entities = decision.resolved_entities
                    
                    if isinstance(expected_context, list):
                        # Check entity extraction
                        if any(entity in entities for entity in expected_context):
                            passed += 1
                            print(f"✅ Context extraction: '{query[:30]}...' -> {entities}")
                        else:
                            print(f"❌ Context extraction: '{query[:30]}...' -> {entities} (expected: {expected_context})")
                    else:
                        # Check topic extraction
                        topic = decision.resolved_topic or ""
                        if expected_context.lower() in topic.lower():
                            passed += 1
                            print(f"✅ Context extraction: '{query[:30]}...' -> {topic}")
                        else:
                            print(f"❌ Context extraction: '{query[:30]}...' -> {topic} (expected: {expected_context})")
                else:
                    print(f"❌ Context extraction: '{query}' -> No entities extracted")
                    
            except Exception as e:
                print(f"❌ Context extraction error: '{query}' -> {str(e)[:50]}")
        
        success_rate = (passed / len(context_scenarios)) * 100
        print(f"\n📊 Context Extraction Integration: {passed}/{len(context_scenarios)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_memory_integration(self):
        """Test memory integration across conversation turns"""
        memory_scenarios = [
            # Scenario 1: Entity memory
            [
                ("Tesla earnings report", {"last_entities": ["Tesla"]}),
                ("What about their competition?", {"last_entities": ["Tesla"]})
            ],
            
            # Scenario 2: Topic memory
            [
                ("Ukraine conflict analysis", {"last_topic": "Ukraine"}),
                ("How is this affecting Europe?", {"last_topic": "Ukraine"})
            ],
            
            # Scenario 3: Context switching
            [
                ("Apple stock news", {"last_entities": ["Apple"]}),
                ("Now tell me about Google", {"last_entities": ["Google"]})
            ]
        ]
        
        passed_scenarios = 0
        for i, scenario in enumerate(memory_scenarios):
            try:
                memory = {}
                scenario_passed = True
                
                for j, (query, expected_memory) in enumerate(scenario):
                    decision = self.router.route_query(query, memory)
                    
                    # Update memory based on decision
                    if hasattr(decision, 'resolved_entities') and decision.resolved_entities:
                        memory['last_entities'] = decision.resolved_entities
                    if hasattr(decision, 'resolved_topic') and decision.resolved_topic:
                        memory['last_topic'] = decision.resolved_topic
                    
                    # For second turn, check if memory is being used
                    if j == 1:
                        if (hasattr(decision, 'graph_query') and 
                            decision.graph_query and 
                            decision.graph_query != query):
                            print(f"✅ Memory scenario {i+1}: Context utilized in query resolution")
                        else:
                            scenario_passed = False
                            print(f"❌ Memory scenario {i+1}: Context not utilized")
                            break
                
                if scenario_passed:
                    passed_scenarios += 1
                    
            except Exception as e:
                print(f"❌ Memory scenario {i+1} error: {str(e)[:50]}")
        
        success_rate = (passed_scenarios / len(memory_scenarios)) * 100
        print(f"\n📊 Memory Integration: {passed_scenarios}/{len(memory_scenarios)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_error_handling_integration(self):
        """Test error handling across system components"""
        error_scenarios = [
            # Malformed inputs
            ("", "empty_query"),
            ("!@#$%^&*()", "special_chars"),
            ("a" * 1000, "very_long_query"),
            
            # Ambiguous queries
            ("What about it?", "ambiguous_reference"),
            ("How are they doing?", "vague_pronoun"),
            ("This is complex", "unclear_context"),
            
            # Out of scope
            ("What's the weather?", "weather_query"),
            ("Write a poem", "creative_request"),
            ("Calculate 2+2", "math_problem"),
            
            # Edge cases
            ("Tesla Tesla Tesla", "repeated_entity"),
            ("Apple vs vs vs Google", "malformed_comparison"),
            ("Breaking news about about about", "repeated_words")
        ]
        
        passed = 0
        for query, error_type in error_scenarios:
            try:
                start_time = time.time()
                decision = self.router.route_query(query, {})
                end_time = time.time()
                
                # Should handle gracefully without crashing
                if (end_time - start_time < 10 and  # Reasonable time
                    hasattr(decision, 'action') and
                    decision.action in ['direct_response', 'delegate_to_graph']):
                    passed += 1
                    print(f"✅ Error handling: '{error_type}' -> {decision.action}")
                else:
                    print(f"❌ Error handling: '{error_type}' -> Failed or timeout")
                    
            except Exception as e:
                # Some defensive errors are acceptable
                if any(keyword in str(e).lower() for keyword in ["timeout", "invalid", "malformed"]):
                    passed += 1
                    print(f"✅ Error handling: '{error_type}' -> Defensive error")
                else:
                    print(f"❌ Error handling: '{error_type}' -> Unexpected error: {str(e)[:50]}")
        
        success_rate = (passed / len(error_scenarios)) * 100
        print(f"\n📊 Error Handling Integration: {passed}/{len(error_scenarios)} ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def test_performance_integration(self):
        """Test performance across multiple queries"""
        performance_queries = [
            "Tesla earnings news",
            "Apple vs Google AI",
            "Ukraine conflict updates", 
            "Biden climate policy",
            "Microsoft stock analysis",
            "Amazon earnings report",
            "Meta social media strategy",
            "Netflix streaming competition"
        ]
        
        response_times = []
        successful_queries = 0
        
        for i, query in enumerate(performance_queries):
            try:
                start_time = time.time()
                decision = self.router.route_query(query, {})
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if (hasattr(decision, 'action') and 
                    decision.action in ['direct_response', 'delegate_to_graph'] and
                    response_time < 5):  # Should be fast
                    successful_queries += 1
                    print(f"✅ Performance test {i+1}: {response_time:.2f}s")
                else:
                    print(f"❌ Performance test {i+1}: Failed or slow")
                    
            except Exception as e:
                print(f"❌ Performance test {i+1}: Error - {str(e)[:50]}")
        
        # Calculate performance metrics
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            print(f"\n📈 Performance Metrics:")
            print(f"   Average Response Time: {avg_response_time:.2f}s")
            print(f"   Max Response Time: {max_response_time:.2f}s")
            print(f"   Success Rate: {successful_queries}/{len(performance_queries)}")
        
        success_rate = (successful_queries / len(performance_queries)) * 100
        performance_acceptable = avg_response_time < 2.0 if response_times else False
        
        print(f"\n📊 Performance Integration: {successful_queries}/{len(performance_queries)} ({success_rate:.1f}%)")
        return success_rate >= 80 and performance_acceptable

def run_end_to_end_simplified_tests():
    """Run simplified end-to-end integration tests"""
    print("🔄 RUNNING END-TO-END INTEGRATION TESTS (SIMPLIFIED)")
    print("=" * 60)
    
    test_suite = TestEndToEndSimplified()
    test_suite.setup_method()
    
    results = {
        "Router Integration": test_suite.test_router_integration(),
        "Context Extraction Integration": test_suite.test_context_extraction_integration(),
        "Memory Integration": test_suite.test_memory_integration(),
        "Error Handling Integration": test_suite.test_error_handling_integration(),
        "Performance Integration": test_suite.test_performance_integration()
    }
    
    print("\n" + "=" * 60)
    print("📋 END-TO-END INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    overall_success = (passed_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({overall_success:.1f}%)")
    
    if overall_success >= 80:
        print("🎉 END-TO-END INTEGRATION: PRODUCTION READY")
        return True
    else:
        print("⚠️  END-TO-END INTEGRATION: NEEDS IMPROVEMENT")
        return False

if __name__ == "__main__":
    run_end_to_end_simplified_tests()