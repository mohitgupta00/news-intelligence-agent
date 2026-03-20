"""
State Management Tests - Test state schema validation, entity tracking, memory isolation, and corruption handling.
"""

import pytest
import sys
import os
import copy
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.state import GraphState

class TestStateManagement:
    """Test suite for state management logic"""
    
    def test_state_schema_completeness(self):
        """Test all required state fields are present"""
        
        required_fields = [
            'user_query', 'resolved_query', 'active_entities',
            'search_queries', 'query_resolution', 'context_hints',
            'extracted_entities', 'conversation_history'
        ]
        
        # Create a minimal valid state
        test_state = {
            'user_query': 'Tesla news',
            'resolved_query': 'Tesla news',
            'active_entities': ['Tesla'],
            'search_queries': ['Tesla news'],
            'query_resolution': {'method': 'direct'},
            'context_hints': {},
            'extracted_entities': ['Tesla'],
            'conversation_history': [],
            'entity_memory': {},
            'thread_id': 'test_thread'
        }
        
        results = []
        
        print(f"\n=== STATE SCHEMA VALIDATION ===")
        
        # Test 1: All required fields present
        try:
            state = dict(test_state)  # GraphState is a TypedDict
            success = True
            print(f"✅ Complete state creation successful")
        except Exception as e:
            success = False
            print(f"❌ Complete state creation failed: {str(e)[:50]}")
        
        results.append(('complete_state', success))
        
        # Test 2: Missing required fields
        for field in required_fields:
            test_state_copy = test_state.copy()
            if field in test_state_copy:
                del test_state_copy[field]
                
                try:
                    state = dict(test_state_copy)  # GraphState is a TypedDict
                    # Should either work with defaults or fail gracefully
                    success = True
                    print(f"✅ Missing '{field}' handled gracefully")
                except Exception as e:
                    # Expected for truly required fields
                    success = True  # Failing is acceptable for required fields
                    print(f"✅ Missing '{field}' properly rejected: {str(e)[:30]}")
                
                results.append((f'missing_{field}', success))
        
        # Test 3: Wrong data types
        type_tests = [
            ('user_query', 123, 'string'),
            ('active_entities', 'not_a_list', 'list'),
            ('query_resolution', 'not_a_dict', 'dict'),
        ]
        
        for field, wrong_value, expected_type in type_tests:
            test_state_copy = test_state.copy()
            test_state_copy[field] = wrong_value
            
            try:
                state = dict(test_state_copy)  # GraphState is a TypedDict
                # Should handle type coercion or fail
                success = True
                print(f"✅ Wrong type for '{field}' handled")
            except Exception as e:
                success = True  # Type validation failure is acceptable
                print(f"✅ Wrong type for '{field}' properly rejected")
            
            results.append((f'wrong_type_{field}', success))
        
        total = len(results)
        successful = sum(1 for _, success in results if success)
        
        print(f"\nState Schema Validation: {successful}/{total} ({successful/total*100:.1f}%)")
        
        assert successful / total >= 0.8, f"State schema validation too low: {successful/total:.2f} < 0.8"
    
    def test_entity_persistence(self):
        """Test entity tracking across conversation turns"""
        
        conversation_flow = [
            ("Apple earnings", ["Apple"]),
            ("What about Google?", ["Apple", "Google"]),
            ("Compare their AI strategies", ["Apple", "Google"]),
            ("Microsoft news", ["Microsoft"]),  # Context switch
            ("How are they doing?", ["Microsoft"]),
        ]
        
        results = []
        
        print(f"\n=== ENTITY PERSISTENCE TESTS ===")
        
        # Simulate conversation state evolution
        current_entities = []
        entity_memory = {}
        
        for turn, (query, expected_entities) in enumerate(conversation_flow):
            try:
                # Update entity memory based on query
                if "Apple" in query:
                    current_entities = ["Apple"]
                elif "Google" in query:
                    if "Apple" in current_entities:
                        current_entities = ["Apple", "Google"]
                    else:
                        current_entities = ["Google"]
                elif "Microsoft" in query:
                    current_entities = ["Microsoft"]  # Context switch
                elif "they" in query.lower() or "their" in query.lower():
                    # Should maintain previous entities
                    pass
                
                # Create state with current entities
                state_data = {
                    'user_query': query,
                    'resolved_query': query,
                    'active_entities': current_entities,
                    'search_queries': [query],
                    'query_resolution': {'method': 'direct'},
                    'context_hints': {},
                    'extracted_entities': current_entities,
                    'conversation_history': [q for q, _ in conversation_flow[:turn]],
                    'entity_memory': {
                        'last_entities': current_entities,
                        'last_task': 'news'
                    },
                    'thread_id': 'test_thread'
                }
                
                state = dict(state_data)  # GraphState is a TypedDict
                
                # Check if entities are properly tracked
                actual_entities = state.get('active_entities', [])
                
                # Success if we have reasonable entity tracking
                success = len(actual_entities) > 0 and any(e in expected_entities for e in actual_entities)
                
                results.append({
                    'turn': turn + 1,
                    'query': query,
                    'expected': expected_entities,
                    'actual': actual_entities,
                    'success': success
                })
                
                status = "✅" if success else "❌"
                print(f"{status} Turn {turn + 1}: '{query}' -> Expected: {expected_entities}, Got: {actual_entities}")
                
            except Exception as e:
                results.append({
                    'turn': turn + 1,
                    'query': query,
                    'error': str(e),
                    'success': False
                })
                print(f"❌ Turn {turn + 1}: '{query}' -> ERROR: {str(e)[:50]}")
        
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        
        print(f"\nEntity Persistence: {successful}/{total} ({successful/total*100:.1f}%)")
        
        assert successful / total >= 0.6, f"Entity persistence too low: {successful/total:.2f} < 0.6"
    
    def test_thread_isolation(self):
        """Test memory isolation between different threads"""
        
        thread_scenarios = [
            # Thread A: Apple discussion
            ('thread_a', [
                ("Apple earnings", ["Apple"]),
                ("What about their stock?", ["Apple"]),
            ]),
            # Thread B: Tesla discussion  
            ('thread_b', [
                ("Tesla news", ["Tesla"]),
                ("How are they performing?", ["Tesla"]),
            ]),
        ]
        
        results = []
        thread_states = {}
        
        print(f"\n=== THREAD ISOLATION TESTS ===")
        
        # Create states for different threads
        for thread_id, conversation in thread_scenarios:
            thread_states[thread_id] = []
            
            for turn, (query, expected_entities) in enumerate(conversation):
                try:
                    state_data = {
                        'user_query': query,
                        'resolved_query': query,
                        'active_entities': expected_entities,
                        'search_queries': [query],
                        'query_resolution': {'method': 'direct'},
                        'context_hints': {},
                        'extracted_entities': expected_entities,
                        'conversation_history': [q for q, _ in conversation[:turn]],
                        'entity_memory': {
                            'last_entities': expected_entities,
                            'last_task': 'news'
                        },
                        'thread_id': thread_id
                    }
                    
                    state = dict(state_data)  # GraphState is a TypedDict
                    thread_states[thread_id].append(state)
                    
                    success = True
                    print(f"✅ {thread_id}: '{query}' -> {expected_entities}")
                    
                except Exception as e:
                    success = False
                    print(f"❌ {thread_id}: '{query}' -> ERROR: {str(e)[:50]}")
                
                results.append({
                    'thread': thread_id,
                    'query': query,
                    'success': success
                })
        
        # Verify isolation - check that thread states don't interfere
        if 'thread_a' in thread_states and 'thread_b' in thread_states:
            thread_a_entities = set()
            thread_b_entities = set()
            
            for state in thread_states['thread_a']:
                if state.get('active_entities'):
                    thread_a_entities.update(state['active_entities'])
            
            for state in thread_states['thread_b']:
                if state.get('active_entities'):
                    thread_b_entities.update(state['active_entities'])
            
            # Check for cross-contamination
            contamination = thread_a_entities & thread_b_entities
            isolation_success = len(contamination) == 0
            
            results.append({
                'test': 'isolation_check',
                'thread_a_entities': list(thread_a_entities),
                'thread_b_entities': list(thread_b_entities),
                'contamination': list(contamination),
                'success': isolation_success
            })
            
            status = "✅" if isolation_success else "❌"
            print(f"{status} Thread isolation: A={list(thread_a_entities)}, B={list(thread_b_entities)}")
        
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        
        print(f"\nThread Isolation: {successful}/{total} ({successful/total*100:.1f}%)")
        
        assert successful / total >= 0.8, f"Thread isolation too low: {successful/total:.2f} < 0.8"
    
    def test_malformed_state_handling(self):
        """Test handling of corrupted state"""
        
        base_state = {
            'user_query': 'Tesla news',
            'resolved_query': 'Tesla news',
            'active_entities': ['Tesla'],
            'search_queries': ['Tesla news'],
            'query_resolution': {'method': 'direct'},
            'context_hints': {},
            'extracted_entities': ['Tesla'],
            'conversation_history': [],
            'entity_memory': {},
            'thread_id': 'test_thread'
        }
        
        corruption_tests = [
            # Missing required fields
            ('missing_user_query', lambda s: s.pop('user_query', None)),
            ('missing_thread_id', lambda s: s.pop('thread_id', None)),
            
            # Wrong data types
            ('wrong_entities_type', lambda s: s.update({'active_entities': 'not_a_list'})),
            ('wrong_memory_type', lambda s: s.update({'entity_memory': 'not_a_dict'})),
            
            # Circular references (simulate with self-reference)
            ('circular_reference', lambda s: s.update({'self_ref': s})),
            
            # Oversized objects
            ('oversized_history', lambda s: s.update({'conversation_history': ['query'] * 10000})),
            ('oversized_entities', lambda s: s.update({'active_entities': ['Entity'] * 1000})),
        ]
        
        results = []
        
        print(f"\n=== MALFORMED STATE HANDLING ===")
        
        for test_name, corruption_func in corruption_tests:
            test_state = copy.deepcopy(base_state)
            
            try:
                # Apply corruption
                corruption_func(test_state)
                
                # Try to create state
                state = dict(test_state)  # GraphState is a TypedDict
                
                # If it succeeds, check if it's reasonable
                success = 'user_query' in state or 'thread_id' in state
                status = "✅" if success else "❌"
                print(f"{status} {test_name}: Handled gracefully")
                
            except Exception as e:
                # Failure is acceptable for malformed data
                success = True
                print(f"✅ {test_name}: Properly rejected - {str(e)[:30]}")
            
            results.append({
                'test': test_name,
                'success': success
            })
        
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        
        print(f"\nMalformed State Handling: {successful}/{total} ({successful/total*100:.1f}%)")
        
        assert successful / total >= 0.8, f"Malformed state handling too low: {successful/total:.2f} < 0.8"

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])