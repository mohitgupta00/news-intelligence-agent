#!/usr/bin/env python3
"""
Simple test to verify system structure and imports work correctly.
Tests the core components without requiring API keys.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_core_imports():
    """Test that all core modules can be imported."""
    print("🧪 Testing Core Module Imports...")
    
    try:
        # Test graph modules
        from graph.modules.query_processing import turn_initializer, query_resolver
        from graph.modules.planning import planner, router
        from graph.modules.execution import fetch_news_node
        from graph.modules.synthesis import synthesizer
        print("✅ Graph modules imported successfully")
        
        # Test utilities
        from utils.text_processing import extract_relevant_chunks, estimate_tokens
        from utils.query_cache import get_cache_stats, clear_query_cache
        from utils.search_memory import get_search_memory_stats
        print("✅ Utility modules imported successfully")
        
        # Test tools
        from tools.fetch_news import fetch_news_async
        from tools.analyze_text import analyze_text_async
        from tools.compare_entities import compare_entities_async
        print("✅ Tool modules imported successfully")
        
        # Test memory
        from memory.checkpointer import get_thread_config
        print("✅ Memory modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_file_structure():
    """Test that key files exist and are properly structured."""
    print("\n🧪 Testing File Structure...")
    
    required_files = [
        'intelligent_router.py',
        'main_orchestrator.py',
        'config.py',
        'requirements.txt',
        'README.md',
        'graph/nodes.py',
        'graph/builder.py',
        'ui/app.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_nodes_file_size():
    """Test that nodes.py is properly modularized (should be small)."""
    print("\n🧪 Testing Modularization...")
    
    try:
        with open('graph/nodes.py', 'r') as f:
            lines = len(f.readlines())
        
        if lines < 60:  # Should be under 60 lines after modularization
            print(f"✅ nodes.py is properly modularized: {lines} lines")
            return True
        else:
            print(f"⚠️ nodes.py might need more modularization: {lines} lines")
            return False
            
    except FileNotFoundError:
        print("❌ nodes.py not found")
        return False

def test_removed_files():
    """Test that unnecessary files have been removed."""
    print("\n🧪 Testing Cleanup...")
    
    removed_files = [
        'debug_comprehensive.py',
        'debug_synthesis.py', 
        'fix_news_issues.py',
        'test_fixes.py',
        'test_memory.py',
        'graph/nodes_old.py'
    ]
    
    still_present = []
    for file_path in removed_files:
        if os.path.exists(file_path):
            still_present.append(file_path)
    
    if still_present:
        print(f"⚠️ Files that should be removed: {still_present}")
        return False
    else:
        print("✅ All unnecessary files have been removed")
        return True

def main():
    """Run all structure tests."""
    print("🚀 NewsIQ System Structure Test")
    print("=" * 50)
    
    tests = [
        ("Core Imports", test_core_imports),
        ("File Structure", test_file_structure), 
        ("Modularization", test_nodes_file_size),
        ("Cleanup", test_removed_files)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    success_rate = passed / len(results) * 100
    print(f"\nSuccess Rate: {passed}/{len(results)} ({success_rate:.1f}%)")
    
    if passed == len(results):
        print("\n🎉 ALL STRUCTURE TESTS PASSED!")
        print("✅ System is properly organized and ready for use")
    else:
        print(f"\n⚠️ {len(results) - passed} tests failed - review needed")
    
    return passed == len(results)

if __name__ == "__main__":
    main()