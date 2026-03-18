"""
Test script for the new LLM-First Router implementation.
Tests the three key scenarios: system capability, news query, and follow-up.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_orchestrator import orchestrator

async def test_system_capability():
    """Test Query 1: 'what can you do?' - should route to direct_response"""
    print("🧪 Testing Query 1: 'what can you do?'")
    print("-" * 50)
    
    result = await orchestrator.process_query("what can you do?", "test_thread_1")
    
    print(f"Routing Decision: {result['routing_decision']}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"Response Preview: {result['response'][:100]}...")
    print()
    
    # Validation
    assert result['routing_decision'] == 'direct_response', "Should route to direct_response"
    assert "NewsIQ" in result['response'], "Should mention NewsIQ"
    assert "news analysis" in result['response'].lower(), "Should mention capabilities"
    
    print("✅ Test 1 PASSED: System capability query handled correctly")
    print("=" * 60)
    return result

async def test_news_query():
    """Test Query 2: 'latest updates on israel iran war' - should delegate to graph"""
    print("🧪 Testing Query 2: 'latest updates on israel iran war'")
    print("-" * 50)
    
    result = await orchestrator.process_query("latest updates on israel iran war", "test_thread_2")
    
    print(f"Routing Decision: {result['routing_decision']}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"Response Preview: {result['response'][:100]}...")
    print()
    
    # Validation
    assert result['routing_decision'] == 'delegate_to_graph', "Should delegate to graph"
    
    print("✅ Test 2 PASSED: News query delegated to graph")
    print("=" * 60)
    return result

async def test_follow_up():
    """Test Follow-up: 'reactions of countries and leaders on this topic' - should use memory"""
    print("🧪 Testing Follow-up: 'reactions of countries and leaders on this topic'")
    print("-" * 50)
    
    # First establish context
    await orchestrator.process_query("latest updates on israel iran war", "test_thread_3")
    
    # Then test follow-up
    result = await orchestrator.process_query("reactions of countries and leaders on this topic", "test_thread_3")
    
    print(f"Routing Decision: {result['routing_decision']}")
    print(f"Reasoning: {result['reasoning']}")
    print(f"Response Preview: {result['response'][:100]}...")
    print()
    
    # Check memory
    memory = orchestrator.conversation_memory.get("test_thread_3", {})
    print(f"Memory Context: {memory.get('conversation_context', 'None')}")
    print(f"Last Entities: {memory.get('last_entities', [])}")
    
    # Validation
    assert result['routing_decision'] == 'delegate_to_graph', "Should delegate to graph"
    assert memory.get('conversation_context') == 'news_analysis', "Should have news analysis context"
    
    print("✅ Test 3 PASSED: Follow-up query with memory context")
    print("=" * 60)
    return result

async def run_all_tests():
    """Run all test scenarios"""
    print("🚀 Starting NewsIQ LLM-First Router Tests")
    print("=" * 60)
    
    try:
        # Test 1: System capability
        await test_system_capability()
        
        # Test 2: News query
        await test_news_query()
        
        # Test 3: Follow-up with memory
        await test_follow_up()
        
        print("🎉 ALL TESTS PASSED!")
        print("✅ LLM-First Router implementation is working correctly")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_all_tests())