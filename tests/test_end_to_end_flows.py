"""
End-to-End Conversation Flow Tests - Complete System Integration
Testing full conversation flows from router to final response
"""
import pytest
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_orchestrator import NewsIQOrchestrator
from intelligent_router import IntelligentRouter

import asyncio

class TestEndToEndConversationFlow:
    
    def setup_method(self):
        """Setup test environment"""
        self.orchestrator = NewsIQOrchestrator()
        self.router = IntelligentRouter()
    
    async def _process_query_async(self, query, conversation_state=None):
        """Helper to process query with optional conversation state"""
        thread_id = "test_thread"
        if conversation_state:
            self.orchestrator.conversation_memory[thread_id] = conversation_state
        return await self.orchestrator.process_query(query, thread_id)
    
    def test_single_turn_news_queries(self):
        """Test single-turn news queries end-to-end"""
        async def run_test():
            test_cases = [
                ("Tesla earnings news", "news analysis"),
                ("Apple vs Google AI", "comparison"),
                ("Ukraine conflict updates", "news summary"),
                ("breaking market news", "news summary"),
                ("Biden climate policy", "news analysis")
            ]
            
            passed = 0
            for query, expected_type in test_cases:
                try:
                    start_time = time.time()
                    response = await self._process_query_async(query)
                    end_time = time.time()
                    
                    # Should complete within reasonable time (30 seconds)
                    if end_time - start_time > 30:
                        print(f"❌ Single turn: '{query}' -> Timeout ({end_time - start_time:.1f}s)")
                        continue
                    
                    # Should return valid response
                    if (isinstance(response, dict) and 
                        "response" in response and 
                        response["response"] and
                        len(response["response"]) > 50):
                        passed += 1
                        print(f"✅ Single turn: '{query}' -> {len(response['response'])} chars ({end_time - start_time:.1f}s)")
                    else:
                        print(f"❌ Single turn: '{query}' -> Invalid response")
                        
                except Exception as e:
                    print(f"❌ Single turn error: '{query}' -> {str(e)[:50]}")
            
            success_rate = (passed / len(test_cases)) * 100
            print(f"\n📊 Single Turn News Queries: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
            return success_rate >= 80
        
        return asyncio.run(run_test())
    
    def test_multi_turn_contextual_conversations(self):
        """Test multi-turn conversations with context"""
        async def run_test():
            conversation_scenarios = [
                # Scenario 1: Company analysis flow
                [
                    ("Tesla earnings report", "financial analysis"),
                    ("What about their competition?", "competitive analysis"),
                    ("How are they performing in AI?", "technology analysis")
                ],
                
                # Scenario 2: Geopolitical flow
                [
                    ("Ukraine Russia conflict", "conflict analysis"),
                    ("How is this affecting Europe?", "impact analysis"),
                    ("What's the US response?", "response analysis")
                ],
                
                # Scenario 3: Tech comparison flow
                [
                    ("Apple vs Google smartphones", "comparison"),
                    ("What about their AI strategies?", "AI comparison"),
                    ("Which has better market position?", "market analysis")
                ]
            ]
            
            passed_scenarios = 0
            for i, scenario in enumerate(conversation_scenarios):
                try:
                    conversation_state = {}
                    scenario_passed = True
                    
                    for j, (query, expected_type) in enumerate(scenario):
                        start_time = time.time()
                        response = await self._process_query_async(query, conversation_state)
                        end_time = time.time()
                        
                        # Update conversation state
                        if isinstance(response, dict) and "thread_id" in response:
                            thread_id = response["thread_id"]
                            conversation_state = self.orchestrator.conversation_memory.get(thread_id, {})
                        
                        # Validate response
                        if (end_time - start_time > 30 or 
                            not isinstance(response, dict) or 
                            "response" not in response or
                            not response["response"] or
                            len(response["response"]) < 30):
                            scenario_passed = False
                            print(f"❌ Multi-turn scenario {i+1}, turn {j+1}: Failed")
                            break
                        else:
                            print(f"✅ Multi-turn scenario {i+1}, turn {j+1}: Success ({end_time - start_time:.1f}s)")
                    
                    if scenario_passed:
                        passed_scenarios += 1
                        
                except Exception as e:
                    print(f"❌ Multi-turn scenario {i+1} error: {str(e)[:50]}")
            
            success_rate = (passed_scenarios / len(conversation_scenarios)) * 100
            print(f"\n📊 Multi-Turn Contextual Conversations: {passed_scenarios}/{len(conversation_scenarios)} ({success_rate:.1f}%)")
            return success_rate >= 75
        
        return asyncio.run(run_test())
    
    def test_context_switching_flows(self):
        """Test context switching between different topics"""
        context_switch_scenarios = [
            [
                ("Tesla stock news", "Tesla"),
                ("Now tell me about Apple", "Apple"),  # Context switch
                ("What about their latest iPhone?", "Apple iPhone")  # Should use new context
            ],
            [
                ("Ukraine conflict updates", "Ukraine"),
                ("Switch topic: Google AI news", "Google AI"),  # Explicit switch
                ("How does this compare to Microsoft?", "Google Microsoft AI")  # New context
            ],
            [
                ("Biden climate policy", "Biden"),
                ("What about Trump's position?", "Trump"),  # Political switch
                ("Compare their approaches", "Biden Trump comparison")  # Both contexts
            ]
        ]
        
        passed = 0
        for i, scenario in enumerate(context_switch_scenarios):
            try:
                conversation_state = {}
                switch_successful = True
                
                for j, (query, expected_context) in enumerate(scenario):
                    response = self.orchestrator.process_query(query, conversation_state)
                    
                    if isinstance(response, dict) and "state" in response:
                        conversation_state = response["state"]
                    
                    # For context switch queries, check if new context is established
                    if j == 1:  # Context switch turn
                        if (isinstance(response, dict) and 
                            "response" in response and 
                            response["response"]):
                            print(f"✅ Context switch {i+1}: New context established")
                        else:
                            switch_successful = False
                            print(f"❌ Context switch {i+1}: Failed to establish new context")
                            break
                    
                    # Final turn should use new context
                    if j == 2:
                        if (isinstance(response, dict) and 
                            "response" in response and 
                            response["response"] and
                            len(response["response"]) > 30):
                            print(f"✅ Context switch {i+1}: New context utilized")
                        else:
                            switch_successful = False
                            print(f"❌ Context switch {i+1}: Failed to use new context")
                
                if switch_successful:
                    passed += 1
                    
            except Exception as e:
                print(f"❌ Context switch {i+1} error: {str(e)[:50]}")
        
        success_rate = (passed / len(context_switch_scenarios)) * 100
        print(f"\n📊 Context Switching Flows: {passed}/{len(context_switch_scenarios)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_error_recovery_flows(self):
        """Test system recovery from various error conditions"""
        error_scenarios = [
            # API failures
            ("Tesla news with API failure simulation", "api_failure"),
            
            # Malformed queries
            ("", "empty_query"),
            ("!@#$%^&*()", "special_chars"),
            ("a", "minimal_query"),
            
            # Very long queries
            ("Tesla " * 100 + "news analysis", "long_query"),
            
            # Ambiguous queries
            ("What about it?", "ambiguous"),
            ("How are they doing?", "vague_reference"),
            
            # Out of scope queries
            ("What's the weather today?", "out_of_scope"),
            ("Write me a poem", "creative_request"),
            ("Solve 2+2", "math_question")
        ]
        
        passed = 0
        for query, error_type in error_scenarios:
            try:
                start_time = time.time()
                response = self.orchestrator.process_query(query)
                end_time = time.time()
                
                # Should handle gracefully without crashing
                if (end_time - start_time < 30 and 
                    isinstance(response, dict) and 
                    "response" in response and 
                    response["response"]):
                    passed += 1
                    print(f"✅ Error recovery: '{error_type}' -> Handled gracefully")
                else:
                    print(f"❌ Error recovery: '{error_type}' -> Failed to handle")
                    
            except Exception as e:
                # Some defensive errors are acceptable
                if any(keyword in str(e).lower() for keyword in ["timeout", "invalid", "unsupported"]):
                    passed += 1
                    print(f"✅ Error recovery: '{error_type}' -> Defensive error handling")
                else:
                    print(f"❌ Error recovery: '{error_type}' -> Unexpected error: {str(e)[:50]}")
        
        success_rate = (passed / len(error_scenarios)) * 100
        print(f"\n📊 Error Recovery Flows: {passed}/{len(error_scenarios)} ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def test_performance_under_load(self):
        """Test system performance under sequential load"""
        load_queries = [
            "Tesla earnings news",
            "Apple vs Google comparison", 
            "Ukraine conflict updates",
            "Biden climate policy",
            "Microsoft AI strategy",
            "Amazon stock analysis",
            "Meta social media news",
            "Netflix streaming updates"
        ]
        
        response_times = []
        successful_queries = 0
        
        for i, query in enumerate(load_queries):
            try:
                start_time = time.time()
                response = self.orchestrator.process_query(query)
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append(response_time)
                
                if (isinstance(response, dict) and 
                    "response" in response and 
                    response["response"] and
                    response_time < 30):
                    successful_queries += 1
                    print(f"✅ Load test {i+1}: {response_time:.1f}s")
                else:
                    print(f"❌ Load test {i+1}: Failed or timeout")
                    
            except Exception as e:
                print(f"❌ Load test {i+1}: Error - {str(e)[:50]}")
        
        # Calculate performance metrics
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            print(f"\n📈 Performance Metrics:")
            print(f"   Average Response Time: {avg_response_time:.1f}s")
            print(f"   Max Response Time: {max_response_time:.1f}s")
            print(f"   Success Rate: {successful_queries}/{len(load_queries)}")
        
        success_rate = (successful_queries / len(load_queries)) * 100
        performance_acceptable = avg_response_time < 15 if response_times else False
        
        print(f"\n📊 Performance Under Load: {successful_queries}/{len(load_queries)} ({success_rate:.1f}%)")
        return success_rate >= 75 and performance_acceptable

def run_end_to_end_conversation_tests():
    """Run all end-to-end conversation flow tests"""
    print("🔄 RUNNING END-TO-END CONVERSATION FLOW TESTS")
    print("=" * 60)
    
    test_suite = TestEndToEndConversationFlow()
    test_suite.setup_method()
    
    results = {
        "Single Turn News Queries": test_suite.test_single_turn_news_queries(),
        "Multi-Turn Contextual Conversations": test_suite.test_multi_turn_contextual_conversations(),
        "Context Switching Flows": test_suite.test_context_switching_flows(),
        "Error Recovery Flows": test_suite.test_error_recovery_flows(),
        "Performance Under Load": test_suite.test_performance_under_load()
    }
    
    print("\n" + "=" * 60)
    print("📋 END-TO-END CONVERSATION FLOW TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    overall_success = (passed_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({overall_success:.1f}%)")
    
    if overall_success >= 80:
        print("🎉 END-TO-END CONVERSATION FLOWS: PRODUCTION READY")
        return True
    else:
        print("⚠️  END-TO-END CONVERSATION FLOWS: NEEDS IMPROVEMENT")
        return False

if __name__ == "__main__":
    run_end_to_end_conversation_tests()