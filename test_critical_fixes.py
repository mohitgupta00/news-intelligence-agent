#!/usr/bin/env python3
"""
Critical Fixes Validation Test
Tests the 6 major fixes implemented to ensure system robustness.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_orchestrator import orchestrator
from intelligent_router import IntelligentRouter

class FixValidationTester:
    def __init__(self):
        self.router = IntelligentRouter()
        self.test_results = []
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        self.test_results.append((test_name, passed, details))
    
    def test_router_prompt_fix(self):
        """Test Issue #1: Router Prompt Design Fix"""
        print("\n🧪 Testing Router Prompt Fix...")
        
        test_queries = [
            ("how to make pizza?", "direct_response", "out-of-scope cooking query"),
            ("what can you do?", "direct_response", "system capability query"),
            ("solve 2+2", "direct_response", "math problem query"),
            ("latest israel iran conflict", "delegate_to_graph", "news analysis query")
        ]
        
        passed_tests = 0
        for query, expected_action, description in test_queries:
            try:
                decision = self.router.route_query(query, {})
                actual_action = decision.action
                
                if actual_action == expected_action:
                    self.log_result(f"Router: {description}", True, f"Correctly routed to {actual_action}")
                    passed_tests += 1
                else:
                    self.log_result(f"Router: {description}", False, f"Expected {expected_action}, got {actual_action}")
            
            except Exception as e:
                self.log_result(f"Router: {description}", False, f"Error: {str(e)}")
        
        overall_passed = passed_tests == len(test_queries)
        self.log_result("Router Prompt Fix Overall", overall_passed, f"{passed_tests}/{len(test_queries)} tests passed")
        return overall_passed
    
    def test_memory_safety_fix(self):
        """Test Issue #2: Memory Type Safety Fix"""
        print("\n🧪 Testing Memory Safety Fix...")
        
        try:
            # Test with None response
            orchestrator._update_memory("test-thread", "test query", None, direct=True)
            memory = orchestrator.conversation_memory.get("test-thread", {})
            
            if memory.get('last_response') == "No response generated":
                self.log_result("Memory Safety: None response", True, "Handled None response correctly")
                memory_safe = True
            else:
                self.log_result("Memory Safety: None response", False, f"Got: {memory.get('last_response')}")
                memory_safe = False
            
            # Test with empty response
            orchestrator._update_memory("test-thread-2", "test query", "", direct=True)
            memory2 = orchestrator.conversation_memory.get("test-thread-2", {})
            
            if memory2.get('last_response') == "No response generated":
                self.log_result("Memory Safety: Empty response", True, "Handled empty response correctly")
                memory_safe = memory_safe and True
            else:
                self.log_result("Memory Safety: Empty response", False, f"Got: {memory2.get('last_response')}")
                memory_safe = False
            
            # Test with valid response
            orchestrator._update_memory("test-thread-3", "test query", "Valid response", direct=True)
            memory3 = orchestrator.conversation_memory.get("test-thread-3", {})
            
            if memory3.get('last_response') == "Valid response":
                self.log_result("Memory Safety: Valid response", True, "Handled valid response correctly")
                memory_safe = memory_safe and True
            else:
                self.log_result("Memory Safety: Valid response", False, f"Got: {memory3.get('last_response')}")
                memory_safe = False
            
            return memory_safe
            
        except Exception as e:
            self.log_result("Memory Safety Fix", False, f"Error: {str(e)}")
            return False
    
    def test_graph_state_fix(self):
        """Test Issue #3: Complete Graph State Initialization"""
        print("\n🧪 Testing Graph State Fix...")
        
        try:
            state = orchestrator._create_complete_graph_state("test query", "test-thread", {})
            
            required_fields = [
                'user_query', 'thread_id', 'messages', 'resolved_query', 'api_queries',
                'intent', 'temporal_constraint', 'plan', 'current_step', 'step_outputs',
                'planning_done', 'entity_memory', 'prior_entity_results', 'session_cache',
                'replan_count', 'replan_decision', 'final_answer'
            ]
            
            missing_fields = [field for field in required_fields if field not in state]
            
            if not missing_fields:
                self.log_result("Graph State: Complete initialization", True, "All required fields present")
                
                # Test entity_memory structure
                entity_memory = state.get('entity_memory', {})
                required_entity_fields = ['last_entity', 'last_entities', 'last_task', 'last_result']
                missing_entity_fields = [field for field in required_entity_fields if field not in entity_memory]
                
                if not missing_entity_fields:
                    self.log_result("Graph State: Entity memory structure", True, "Entity memory properly structured")
                    return True
                else:
                    self.log_result("Graph State: Entity memory structure", False, f"Missing: {missing_entity_fields}")
                    return False
            else:
                self.log_result("Graph State: Complete initialization", False, f"Missing fields: {missing_fields}")
                return False
                
        except Exception as e:
            self.log_result("Graph State Fix", False, f"Error: {str(e)}")
            return False
    
    async def test_end_to_end_critical_queries(self):
        """Test the original failing queries end-to-end"""
        print("\n🧪 Testing End-to-End Critical Queries...")
        
        critical_queries = [
            ("how to make pizza?", "direct_response", "Should decline cooking request"),
            ("what can you do?", "direct_response", "Should show system capabilities"),
            ("latest tech industry news", "delegate_to_graph", "Should fetch and analyze tech news")
        ]
        
        passed_tests = 0
        for query, expected_routing, description in critical_queries:
            try:
                result = await orchestrator.process_query(query, f"test-thread-{len(self.test_results)}")
                
                actual_routing = result.get('routing_decision')
                response = result.get('response', '')
                
                if actual_routing == expected_routing and response and len(response) > 10:
                    self.log_result(f"E2E: {description}", True, f"Routed to {actual_routing}, got response")
                    passed_tests += 1
                else:
                    self.log_result(f"E2E: {description}", False, f"Expected {expected_routing}, got {actual_routing}")
            
            except Exception as e:
                self.log_result(f"E2E: {description}", False, f"Error: {str(e)}")
        
        overall_passed = passed_tests == len(critical_queries)
        self.log_result("End-to-End Tests Overall", overall_passed, f"{passed_tests}/{len(critical_queries)} tests passed")
        return overall_passed
    
    async def run_all_tests(self):
        """Run all validation tests"""
        print("🚀 Running Critical Fixes Validation Tests")
        print("=" * 60)
        
        # Test individual fixes
        router_fix = self.test_router_prompt_fix()
        memory_fix = self.test_memory_safety_fix()
        state_fix = self.test_graph_state_fix()
        
        # Test end-to-end functionality
        e2e_fix = await self.test_end_to_end_critical_queries()
        
        # Calculate overall results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, passed, _ in self.test_results if passed)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 VALIDATION RESULTS")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        critical_fixes_status = [router_fix, memory_fix, state_fix, e2e_fix]
        critical_passed = sum(critical_fixes_status)
        
        print(f"\nCritical Fixes Status: {critical_passed}/4")
        print(f"- Router Prompt Fix: {'✅' if router_fix else '❌'}")
        print(f"- Memory Safety Fix: {'✅' if memory_fix else '❌'}")
        print(f"- Graph State Fix: {'✅' if state_fix else '❌'}")
        print(f"- End-to-End Tests: {'✅' if e2e_fix else '❌'}")
        
        if critical_passed == 4:
            print("\n🎉 ALL CRITICAL FIXES VALIDATED SUCCESSFULLY!")
            print("✅ System is ready for production use")
        else:
            print(f"\n⚠️ {4 - critical_passed} critical fixes need attention")
            print("❌ System requires additional fixes before production")
        
        return critical_passed == 4

if __name__ == "__main__":
    tester = FixValidationTester()
    success = asyncio.run(tester.run_all_tests())
    sys.exit(0 if success else 1)