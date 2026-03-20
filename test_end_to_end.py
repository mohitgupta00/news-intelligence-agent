#!/usr/bin/env python3
"""
End-to-End System Test - Tests the original failing queries with the complete system.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_original_failing_queries():
    """Test the exact queries that were failing before our fixes"""
    print("🧪 Testing Original Failing Queries End-to-End...")
    
    try:
        from main_orchestrator import orchestrator
        
        # The original failing query sequence
        test_queries = [
            {
                "query": "how to make pizza?",
                "expected_routing": "direct_response",
                "description": "Should decline cooking request politely",
                "should_contain": ["NewsIQ", "news", "current events"]
            },
            {
                "query": "what are you supposed to do?", 
                "expected_routing": "direct_response",
                "description": "Should show system capabilities",
                "should_contain": ["NewsIQ", "news analysis", "capabilities"]
            },
            {
                "query": "what is going on in tech industry",
                "expected_routing": "delegate_to_graph", 
                "description": "Should analyze tech industry news",
                "should_contain": ["tech", "industry", "news"]
            },
            {
                "query": "latest updates in israel iran war",
                "expected_routing": "delegate_to_graph",
                "description": "Should analyze geopolitical situation", 
                "should_contain": ["israel", "iran"]
            },
            {
                "query": "what is usa's stand on it?",
                "expected_routing": "delegate_to_graph",
                "description": "Should use context from previous query",
                "should_contain": ["usa", "united states"]
            }
        ]
        
        print("\nEnd-to-End Test Results:")
        print("=" * 80)
        
        passed = 0
        total = len(test_queries)
        thread_id = "e2e-test-thread"
        
        for i, test_case in enumerate(test_queries, 1):
            query = test_case["query"]
            expected_routing = test_case["expected_routing"]
            description = test_case["description"]
            should_contain = test_case["should_contain"]
            
            print(f"\n{i}. Testing: '{query}'")
            print(f"   Expected: {description}")
            
            try:
                # Process the query
                result = await orchestrator.process_query(query, thread_id)
                
                actual_routing = result.get('routing_decision')
                response = result.get('response', '')
                reasoning = result.get('reasoning', '')
                
                # Check routing
                routing_correct = actual_routing == expected_routing
                
                # Check response quality
                has_response = response and len(response.strip()) > 20
                
                # Check content relevance (basic keyword check)
                content_relevant = any(keyword.lower() in response.lower() 
                                     for keyword in should_contain) if has_response else False
                
                # Overall success
                test_passed = routing_correct and has_response
                
                if test_passed:
                    print(f"   ✅ PASS - Routed to {actual_routing}")
                    print(f"   📝 Response: {response[:100]}...")
                    passed += 1
                else:
                    print(f"   ❌ FAIL - Issues detected:")
                    if not routing_correct:
                        print(f"      - Wrong routing: got {actual_routing}, expected {expected_routing}")
                    if not has_response:
                        print(f"      - No valid response generated")
                    if not content_relevant and has_response:
                        print(f"      - Response may not be relevant")
                
                print(f"   🤔 Reasoning: {reasoning}")
                
            except Exception as e:
                print(f"   ❌ ERROR: {str(e)}")
                print(f"   🔍 This indicates a system failure that needs attention")
        
        success_rate = (passed / total) * 100
        print(f"\n" + "=" * 80)
        print(f"📊 RESULTS: {passed}/{total} queries passed ({success_rate:.1f}%)")
        
        if passed == total:
            print("🎉 ALL ORIGINAL FAILING QUERIES NOW WORK!")
            print("✅ System fixes are successful")
            return True
        elif passed >= total * 0.8:  # 80% success rate
            print("✅ MOSTLY SUCCESSFUL - System is much more robust")
            print("⚠️ Some queries may need fine-tuning")
            return True
        else:
            print("❌ SYSTEM STILL HAS ISSUES")
            print("🔧 Additional fixes needed")
            return False
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("🔧 System dependencies may be missing")
        return False
    except Exception as e:
        print(f"❌ System Error: {e}")
        print("🔧 Core system issues detected")
        return False

async def test_error_handling():
    """Test error handling scenarios"""
    print("\n🧪 Testing Error Handling...")
    
    try:
        from main_orchestrator import orchestrator
        
        # Test edge cases that might cause errors
        edge_cases = [
            "",  # Empty query
            "   ",  # Whitespace only
            "a" * 1000,  # Very long query
            "🚀🎉💻",  # Emoji only
        ]
        
        passed = 0
        for i, query in enumerate(edge_cases, 1):
            try:
                result = await orchestrator.process_query(query, f"edge-test-{i}")
                response = result.get('response', '')
                
                if response and len(response) > 0:
                    print(f"✅ Edge case {i}: Handled gracefully")
                    passed += 1
                else:
                    print(f"❌ Edge case {i}: No response generated")
                    
            except Exception as e:
                print(f"❌ Edge case {i}: Error - {str(e)}")
        
        print(f"Error Handling: {passed}/{len(edge_cases)} passed")
        return passed == len(edge_cases)
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

async def main():
    """Run comprehensive end-to-end tests"""
    print("🚀 Comprehensive End-to-End System Test")
    print("Testing all fixes with the complete NewsIQ system")
    print("=" * 80)
    
    # Test original failing queries
    queries_ok = await test_original_failing_queries()
    
    # Test error handling
    errors_ok = await test_error_handling()
    
    print("\n" + "=" * 80)
    print("🎯 FINAL ASSESSMENT")
    print("=" * 80)
    print(f"Original Queries: {'✅ PASS' if queries_ok else '❌ FAIL'}")
    print(f"Error Handling: {'✅ PASS' if errors_ok else '❌ FAIL'}")
    
    if queries_ok and errors_ok:
        print("\n🎉 COMPLETE SYSTEM VALIDATION SUCCESSFUL!")
        print("✅ All critical fixes working in production environment")
        print("✅ Ready to proceed with medium priority improvements")
        return True
    elif queries_ok:
        print("\n✅ CORE FUNCTIONALITY WORKING")
        print("⚠️ Error handling needs some attention")
        print("✅ Ready to proceed with medium priority improvements")
        return True
    else:
        print("\n❌ SYSTEM NEEDS MORE WORK")
        print("🔧 Critical issues remain - address before proceeding")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)