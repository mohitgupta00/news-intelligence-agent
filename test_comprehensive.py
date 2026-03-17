#!/usr/bin/env python3
"""Comprehensive test suite for all implemented fixes and end-to-end system validation."""

import sys
import os
import asyncio
import time
import json
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.builder import graph
from memory.checkpointer import get_thread_config
from utils.text_processing import extract_relevant_chunks, estimate_tokens
from utils.query_cache import get_cached_resolution, cache_query_resolution, get_cache_stats, clear_query_cache
from utils.search_memory import store_search_result, should_reuse_search_results, clear_search_memory

class TestResults:
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
    
    def add_result(self, test_name: str, passed: bool, details: str = ""):
        self.results[test_name] = {
            'passed': passed,
            'details': details,
            'timestamp': time.time()
        }
    
    def get_summary(self) -> Dict:
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r['passed'])
        return {
            'total_tests': total,
            'passed': passed,
            'failed': total - passed,
            'success_rate': f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            'duration': f"{time.time() - self.start_time:.2f}s"
        }

def test_fix_1_rag_context_extraction(results: TestResults):
    """Test Issue #1: RAG-based Context Extraction"""
    print("🧪 Testing Fix #1: RAG Context Extraction...")
    
    # Create mock step outputs with varying relevance
    mock_step_outputs = {
        0: {
            'tool': 'fetch_news',
            'result': 'OpenAI announced GPT-5 with revolutionary capabilities. The new model shows significant improvements in reasoning and multimodal understanding. CEO Sam Altman highlighted the breakthrough in artificial general intelligence research.' * 5
        },
        1: {
            'tool': 'fetch_news', 
            'result': 'Tesla stock prices fluctuated today amid market volatility. Elon Musk commented on production targets for the upcoming quarter. Electric vehicle sales continue to grow globally.' * 3
        },
        2: {
            'tool': 'analyze_text',
            'result': 'Weather patterns show unusual activity this season. Climate scientists are monitoring temperature changes across multiple regions.' * 2
        }
    }
    
    # Test 1: Relevant extraction for OpenAI query
    openai_query = "What are the latest OpenAI developments?"
    relevant_chunks = extract_relevant_chunks(mock_step_outputs, openai_query, max_tokens=500)
    token_count = estimate_tokens(relevant_chunks)
    contains_openai = 'OpenAI' in relevant_chunks and 'GPT-5' in relevant_chunks
    
    test1_passed = token_count < 500 and contains_openai
    results.add_result("RAG_token_limit", test1_passed, f"Tokens: {token_count}/500, Contains OpenAI: {contains_openai}")
    
    # Test 2: Irrelevant content filtering
    weather_query = "What's the weather like?"
    weather_chunks = extract_relevant_chunks(mock_step_outputs, weather_query, max_tokens=300)
    weather_relevant = 'weather' in weather_chunks.lower() or 'climate' in weather_chunks.lower()
    no_tesla = 'Tesla' not in weather_chunks
    
    test2_passed = weather_relevant and no_tesla
    results.add_result("RAG_relevance_filtering", test2_passed, f"Weather relevant: {weather_relevant}, Tesla filtered: {no_tesla}")
    
    # Test 3: Empty input handling
    empty_chunks = extract_relevant_chunks({}, "test query", max_tokens=100)
    test3_passed = empty_chunks == ""
    results.add_result("RAG_empty_handling", test3_passed, f"Empty input handled: {test3_passed}")
    
    print(f"✅ RAG Tests: {sum(1 for t in ['RAG_token_limit', 'RAG_relevance_filtering', 'RAG_empty_handling'] if results.results[t]['passed'])}/3 passed")

def test_fix_2_query_caching(results: TestResults):
    """Test Issue #2: Query Resolution Caching"""
    print("🧪 Testing Fix #2: Query Resolution Caching...")
    
    clear_query_cache()
    
    # Test 1: Cache storage and retrieval
    original_query = "What is happening with Apple?"
    resolved_query = "What is happening with Apple Inc latest news developments?"
    cache_query_resolution(original_query, resolved_query)
    
    cached_result = get_cached_resolution(original_query)
    test1_passed = cached_result == resolved_query
    results.add_result("Cache_exact_match", test1_passed, f"Cached correctly: {test1_passed}")
    
    # Test 2: Similar query matching
    similar_query = "What's happening with Apple?"
    similar_result = get_cached_resolution(similar_query)
    test2_passed = similar_result is not None
    results.add_result("Cache_similar_match", test2_passed, f"Similar match found: {test2_passed}")
    
    # Test 3: Cache statistics
    stats = get_cache_stats()
    test3_passed = stats['total_entries'] > 0
    results.add_result("Cache_stats", test3_passed, f"Stats working: {stats}")
    
    # Test 4: Unrelated query
    unrelated_result = get_cached_resolution("Weather forecast for tomorrow")
    test4_passed = unrelated_result is None
    results.add_result("Cache_unrelated_filtering", test4_passed, f"Unrelated filtered: {test4_passed}")
    
    print(f"✅ Cache Tests: {sum(1 for t in ['Cache_exact_match', 'Cache_similar_match', 'Cache_stats', 'Cache_unrelated_filtering'] if results.results[t]['passed'])}/4 passed")

def test_fix_3_modular_architecture(results: TestResults):
    """Test Issue #3: Modular Architecture"""
    print("🧪 Testing Fix #3: Modular Architecture...")
    
    # Test 1: Module imports work
    try:
        from graph.modules.query_processing import turn_initializer, query_resolver
        from graph.modules.planning import planner, router
        from graph.modules.execution import fetch_news_node
        from graph.modules.synthesis import synthesizer
        test1_passed = True
    except ImportError as e:
        test1_passed = False
    
    results.add_result("Modular_imports", test1_passed, f"All modules importable: {test1_passed}")
    
    # Test 2: Individual node functionality
    mock_state = {
        'user_query': 'test query',
        'thread_id': 'test',
        'entity_memory': {'last_entity': None, 'last_entities': [], 'last_task': None, 'last_result': None}
    }
    
    try:
        init_result = turn_initializer(mock_state)
        test2_passed = isinstance(init_result, dict) and 'plan' in init_result
    except Exception:
        test2_passed = False
    
    results.add_result("Modular_node_execution", test2_passed, f"Node execution works: {test2_passed}")
    
    # Test 3: File size reduction
    try:
        with open('graph/nodes.py', 'r') as f:
            new_lines = len(f.readlines())
        with open('graph/nodes_old.py', 'r') as f:
            old_lines = len(f.readlines())
        
        reduction = (old_lines - new_lines) / old_lines * 100
        test3_passed = reduction > 80  # Should be ~88% reduction
    except FileNotFoundError:
        test3_passed = False
        reduction = 0
    
    results.add_result("Modular_size_reduction", test3_passed, f"Size reduction: {reduction:.1f}%")
    
    print(f"✅ Modular Tests: {sum(1 for t in ['Modular_imports', 'Modular_node_execution', 'Modular_size_reduction'] if results.results[t]['passed'])}/3 passed")

def test_fix_4_search_memory(results: TestResults):
    """Test Issue #4: Persistent Search Memory"""
    print("🧪 Testing Fix #4: Search Memory...")
    
    thread_id = "test-memory-validation"
    clear_search_memory(thread_id)
    
    # Test 1: Memory storage
    store_search_result(thread_id, "Tesla news", "Tesla announced new model with advanced features", {"source": "test"})
    should_reuse, results_list = should_reuse_search_results("Tesla news", thread_id)
    test1_passed = should_reuse and len(results_list) > 0
    results.add_result("Memory_storage", test1_passed, f"Storage works: {test1_passed}")
    
    # Test 2: Similar query detection
    should_reuse_similar, similar_results = should_reuse_search_results("What about Tesla?", thread_id)
    test2_passed = len(similar_results) > 0  # Should find similar even if not exact match
    results.add_result("Memory_similarity", test2_passed, f"Similarity detection: {test2_passed}")
    
    # Test 3: Memory isolation (different thread)
    other_thread = "other-thread"
    should_reuse_other, other_results = should_reuse_search_results("Tesla news", other_thread)
    test3_passed = not should_reuse_other and len(other_results) == 0
    results.add_result("Memory_isolation", test3_passed, f"Thread isolation: {test3_passed}")
    
    print(f"✅ Memory Tests: {sum(1 for t in ['Memory_storage', 'Memory_similarity', 'Memory_isolation'] if results.results[t]['passed'])}/3 passed")

async def test_end_to_end_workflow(results: TestResults):
    """Test complete end-to-end workflow"""
    print("🧪 Testing End-to-End Workflow...")
    
    thread_id = "e2e-test-thread"
    
    # Test 1: Basic query processing
    test_state = {
        'user_query': 'What is happening with Microsoft?',
        'thread_id': thread_id,
        'messages': [],
        'resolved_query': '',
        'api_queries': [],
        'intent': '',
        'temporal_constraint': None,
        'plan': [],
        'current_step': 0,
        'step_outputs': {},
        'planning_done': False,
        'entity_memory': {
            'last_entity': None,
            'last_entities': [],
            'last_task': None,
            'last_result': None
        },
        'prior_entity_results': [],
        'session_cache': {},
        'replan_count': 0,
        'replan_decision': None,
        'final_answer': None
    }
    
    config = get_thread_config(thread_id)
    
    try:
        start_time = time.time()
        result1 = await graph.ainvoke(test_state, config)
        execution_time = time.time() - start_time
        
        has_answer = result1.get('final_answer') is not None
        reasonable_time = execution_time < 30
        has_plan = len(result1.get('plan', [])) > 0
        
        test1_passed = has_answer and reasonable_time and has_plan
        results.add_result("E2E_basic_workflow", test1_passed, 
                         f"Answer: {has_answer}, Time: {execution_time:.2f}s, Plan: {has_plan}")
        
    except Exception as e:
        test1_passed = False
        results.add_result("E2E_basic_workflow", False, f"Error: {str(e)}")
    
    # Test 2: Follow-up query (context resolution)
    if test1_passed:
        try:
            followup_state = result1.copy()
            followup_state['user_query'] = 'What about their AI initiatives?'
            
            start_time = time.time()
            result2 = await graph.ainvoke(followup_state, config)
            followup_time = time.time() - start_time
            
            has_followup_answer = result2.get('final_answer') is not None
            context_preserved = result2.get('entity_memory', {}).get('last_entities') is not None
            
            test2_passed = has_followup_answer and context_preserved
            results.add_result("E2E_context_resolution", test2_passed,
                             f"Followup answer: {has_followup_answer}, Context: {context_preserved}, Time: {followup_time:.2f}s")
            
        except Exception as e:
            results.add_result("E2E_context_resolution", False, f"Error: {str(e)}")
    else:
        results.add_result("E2E_context_resolution", False, "Skipped due to basic workflow failure")
    
    # Test 3: Out-of-scope query handling
    try:
        oos_state = test_state.copy()
        oos_state['user_query'] = 'What will Microsoft stock price be tomorrow?'
        
        result3 = await graph.ainvoke(oos_state, config)
        oos_answer = result3.get('final_answer', '')
        
        properly_rejected = ('prediction' in oos_answer.lower() or 
                           'stock price' in oos_answer.lower() or
                           'investment advice' in oos_answer.lower())
        
        test3_passed = properly_rejected
        results.add_result("E2E_oos_handling", test3_passed, f"OOS properly handled: {test3_passed}")
        
    except Exception as e:
        results.add_result("E2E_oos_handling", False, f"Error: {str(e)}")
    
    print(f"✅ E2E Tests: {sum(1 for t in ['E2E_basic_workflow', 'E2E_context_resolution', 'E2E_oos_handling'] if results.results[t]['passed'])}/3 passed")

async def test_performance_benchmarks(results: TestResults):
    """Test performance benchmarks"""
    print("🧪 Testing Performance Benchmarks...")
    
    # Test 1: Response time under load
    thread_id = "perf-test-thread"
    queries = [
        "What is happening with Google?",
        "Tell me about Amazon news",
        "What about Apple developments?",
        "Microsoft latest updates",
        "Tesla recent announcements"
    ]
    
    times = []
    successes = 0
    
    for i, query in enumerate(queries):
        test_state = {
            'user_query': query,
            'thread_id': f"{thread_id}-{i}",
            'messages': [],
            'resolved_query': '',
            'api_queries': [],
            'intent': '',
            'temporal_constraint': None,
            'plan': [],
            'current_step': 0,
            'step_outputs': {},
            'planning_done': False,
            'entity_memory': {'last_entity': None, 'last_entities': [], 'last_task': None, 'last_result': None},
            'prior_entity_results': [],
            'session_cache': {},
            'replan_count': 0,
            'replan_decision': None,
            'final_answer': None
        }
        
        try:
            start_time = time.time()
            result = await graph.ainvoke(test_state, get_thread_config(f"{thread_id}-{i}"))
            execution_time = time.time() - start_time
            
            if result.get('final_answer'):
                times.append(execution_time)
                successes += 1
                
        except Exception:
            pass
    
    avg_time = sum(times) / len(times) if times else float('inf')
    success_rate = successes / len(queries)
    
    perf_passed = avg_time < 10 and success_rate >= 0.8  # 80% success rate, <10s avg
    results.add_result("Performance_load_test", perf_passed, 
                     f"Avg time: {avg_time:.2f}s, Success rate: {success_rate:.1%}")
    
    print(f"✅ Performance Tests: {1 if perf_passed else 0}/1 passed")

def print_detailed_results(results: TestResults):
    """Print detailed test results"""
    print("\n" + "="*80)
    print("📊 DETAILED TEST RESULTS")
    print("="*80)
    
    categories = {
        'Fix #1 - RAG Context': ['RAG_token_limit', 'RAG_relevance_filtering', 'RAG_empty_handling'],
        'Fix #2 - Query Cache': ['Cache_exact_match', 'Cache_similar_match', 'Cache_stats', 'Cache_unrelated_filtering'],
        'Fix #3 - Modular Arch': ['Modular_imports', 'Modular_node_execution', 'Modular_size_reduction'],
        'Fix #4 - Search Memory': ['Memory_storage', 'Memory_similarity', 'Memory_isolation'],
        'End-to-End Tests': ['E2E_basic_workflow', 'E2E_context_resolution', 'E2E_oos_handling'],
        'Performance Tests': ['Performance_load_test']
    }
    
    for category, test_names in categories.items():
        print(f"\n{category}:")
        category_passed = 0
        category_total = 0
        
        for test_name in test_names:
            if test_name in results.results:
                test_result = results.results[test_name]
                status = "✅ PASS" if test_result['passed'] else "❌ FAIL"
                print(f"  {test_name}: {status} - {test_result['details']}")
                if test_result['passed']:
                    category_passed += 1
                category_total += 1
        
        if category_total > 0:
            print(f"  → Category Score: {category_passed}/{category_total} ({category_passed/category_total*100:.1f}%)")

async def main():
    """Run comprehensive test suite"""
    print("🚀 COMPREHENSIVE TEST SUITE - News Intelligence Agent")
    print("="*80)
    
    results = TestResults()
    
    # Run all test categories
    test_fix_1_rag_context_extraction(results)
    test_fix_2_query_caching(results)
    test_fix_3_modular_architecture(results)
    test_fix_4_search_memory(results)
    await test_end_to_end_workflow(results)
    await test_performance_benchmarks(results)
    
    # Print detailed results
    print_detailed_results(results)
    
    # Print summary
    summary = results.get_summary()
    print(f"\n" + "="*80)
    print("🎯 FINAL SUMMARY")
    print("="*80)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"Total Duration: {summary['duration']}")
    
    if summary['passed'] == summary['total_tests']:
        print("\n🎉 ALL TESTS PASSED! System is production-ready.")
    elif summary['passed'] / summary['total_tests'] >= 0.8:
        print(f"\n✅ MOSTLY SUCCESSFUL! {summary['success_rate']} pass rate is acceptable.")
    else:
        print(f"\n⚠️  NEEDS ATTENTION! {summary['success_rate']} pass rate requires fixes.")
    
    return summary['passed'] == summary['total_tests']

if __name__ == "__main__":
    asyncio.run(main())