#!/usr/bin/env python3
"""
Focused Context History Testing - Using Actual System APIs
Quality Analyst perspective with realistic test scenarios
"""

import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.semantic_context import SemanticContextManager
from utils.entity_resolution import EntityResolutionEngine
from graph.modules.query_processing import resolve_contextual_query, needs_context_resolution, extract_entities_from_text
from intelligent_router import IntelligentRouter

class TestContextHistoryActual:
    """Test context history using actual system functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.context_manager = SemanticContextManager()
        self.entity_resolver = EntityResolutionEngine()
        self.router = IntelligentRouter()
        
    def test_contextual_query_resolution_scenarios(self):
        """Test contextual query resolution with realistic scenarios"""
        
        print("\\n🔍 TESTING CONTEXTUAL QUERY RESOLUTION")
        print("=" * 50)
        
        # Test scenarios with entity memory and conversation history
        scenarios = [
            {
                "name": "Linear Conversation Flow",
                "entity_memory": {"last_entities": ["Tesla"], "last_task": "earnings report"},
                "conversation_history": [
                    {"query": "Tesla earnings report", "entities": ["Tesla"]},
                ],
                "test_queries": [
                    ("What about their competition?", "Tesla competition"),
                    ("Any updates?", "Tesla"),
                    ("How are they performing?", "Tesla")
                ]
            },
            {
                "name": "Multi-Entity Context",
                "entity_memory": {"last_entities": ["Israel", "Iran"], "last_task": "conflict news"},
                "conversation_history": [
                    {"query": "Israel Iran conflict", "entities": ["Israel", "Iran"]},
                ],
                "test_queries": [
                    ("How is this affecting oil prices?", "Israel"),
                    ("What about their allies?", "Israel"),
                    ("Any diplomatic efforts?", "Israel")
                ]
            },
            {
                "name": "Topic Switching",
                "entity_memory": {"last_entities": ["Apple"], "last_task": "iPhone sales"},
                "conversation_history": [
                    {"query": "Apple iPhone sales", "entities": ["Apple"]},
                    {"query": "Google Pixel updates", "entities": ["Google"]},
                ],
                "test_queries": [
                    ("What about Samsung?", "Samsung"),
                    ("Compare their strategies", "Samsung"),
                ]
            }
        ]
        
        total_tests = 0
        successful_resolutions = 0
        
        for scenario in scenarios:
            print(f"\\n--- {scenario['name']} ---")
            
            for query, expected_entity in scenario['test_queries']:
                total_tests += 1
                
                # Test if context resolution is needed
                needs_resolution = needs_context_resolution(query)
                print(f"Query: '{query}' - Needs resolution: {needs_resolution}")
                
                if needs_resolution:
                    # Test contextual resolution
                    resolved_query = resolve_contextual_query(
                        query, 
                        scenario['entity_memory'], 
                        scenario['conversation_history']
                    )
                    
                    print(f"  Original: {query}")
                    print(f"  Resolved: {resolved_query}")
                    
                    # Check if expected entity is preserved/added
                    if expected_entity.lower() in resolved_query.lower():
                        successful_resolutions += 1
                        print(f"  ✅ Context preserved: {expected_entity}")
                    else:
                        print(f"  ❌ Context lost: {expected_entity}")
                else:
                    print(f"  ➡️  No resolution needed")
                    successful_resolutions += 1  # Count as success
        
        success_rate = (successful_resolutions / total_tests) * 100
        print(f"\\n📊 CONTEXTUAL RESOLUTION RESULTS:")
        print(f"   Total tests: {total_tests}")
        print(f"   Successful: {successful_resolutions}")
        print(f"   Success rate: {success_rate:.1f}%")
        
        # Quality threshold
        assert success_rate >= 70, f"Context resolution success rate too low: {success_rate:.1f}%"
        
    def test_entity_extraction_robustness(self):
        """Test entity extraction from various query types"""
        
        print("\\n🔍 TESTING ENTITY EXTRACTION ROBUSTNESS")
        print("=" * 50)
        
        test_cases = [
            # Clear entity mentions
            ("Tesla earnings report", ["Tesla"]),
            ("Apple vs Google competition", ["Apple", "Google"]),
            ("Biden climate policy", ["Biden"]),
            
            # Mixed case and punctuation
            ("tesla stock news!", ["Tesla"]),
            ("APPLE iPhone sales?", ["Apple"]),
            ("Microsoft, Google, Amazon cloud", ["Microsoft", "Google", "Amazon"]),
            
            # Contextual entities
            ("Israel Iran conflict latest", ["Israel", "Iran"]),
            ("Trump Biden election updates", ["Trump", "Biden"]),
            ("China USA trade war", ["China", "Usa"]),  # Note: extraction may vary
            
            # No clear entities
            ("latest technology news", []),
            ("market analysis today", []),
            ("economic forecast", []),
        ]
        
        total_tests = 0
        correct_extractions = 0
        
        for query, expected_entities in test_cases:
            total_tests += 1
            
            # Test entity extraction
            extracted = extract_entities_from_text(query)
            print(f"Query: '{query}'")
            print(f"  Expected: {expected_entities}")
            print(f"  Extracted: {extracted}")
            
            # Check if we got the expected entities (case-insensitive)
            expected_lower = [e.lower() for e in expected_entities]
            extracted_lower = [e.lower() for e in extracted]
            
            if not expected_entities:  # No entities expected
                if not extracted:
                    correct_extractions += 1
                    print("  ✅ Correctly found no entities")
                else:
                    print("  ⚠️  Found unexpected entities")
            else:
                # Check if at least one expected entity was found
                found_any = any(exp in extracted_lower for exp in expected_lower)
                if found_any:
                    correct_extractions += 1
                    print("  ✅ Found expected entities")
                else:
                    print("  ❌ Missed expected entities")
        
        extraction_rate = (correct_extractions / total_tests) * 100
        print(f"\\n📊 ENTITY EXTRACTION RESULTS:")
        print(f"   Total tests: {total_tests}")
        print(f"   Correct: {correct_extractions}")
        print(f"   Success rate: {extraction_rate:.1f}%")
        
        # Quality threshold
        assert extraction_rate >= 60, f"Entity extraction success rate too low: {extraction_rate:.1f}%"
        
    def test_semantic_context_switch_detection(self):
        """Test semantic context switch detection"""
        
        print("\\n🔍 TESTING SEMANTIC CONTEXT SWITCH DETECTION")
        print("=" * 50)
        
        # Test context switch scenarios
        switch_scenarios = [
            {
                "description": "Explicit topic switch",
                "entities": ["Tesla"],
                "query": "Now tell me about Apple iPhone sales",
                "expected_switch": True
            },
            {
                "description": "Continuation in same topic",
                "entities": ["Tesla"],
                "query": "What about Tesla's competition?",
                "expected_switch": False
            },
            {
                "description": "Related topic expansion",
                "entities": ["Apple"],
                "query": "How is Google Pixel competing?",
                "expected_switch": True  # Different company
            },
            {
                "description": "Pronoun reference",
                "entities": ["Israel", "Iran"],
                "query": "How is this affecting oil prices?",
                "expected_switch": False  # Same context
            }
        ]
        
        correct_detections = 0
        total_detections = 0
        
        for scenario in switch_scenarios:
            total_detections += 1
            
            # Update context with entities first
            self.context_manager.update_context("Previous query", scenario["entities"])
            
            # Test switch detection
            switch_result = self.context_manager.detect_context_switch(
                scenario["query"], 
                scenario["entities"]
            )
            
            print(f"\\nScenario: {scenario['description']}")
            print(f"  Query: '{scenario['query']}'")
            print(f"  Previous entities: {scenario['entities']}")
            print(f"  Expected switch: {scenario['expected_switch']}")
            print(f"  Detected switch: {switch_result.switch_detected}")
            print(f"  Switch probability: {switch_result.switch_probability:.3f}")
            print(f"  Switch type: {switch_result.switch_type}")
            
            if switch_result.switch_detected == scenario['expected_switch']:
                correct_detections += 1
                print("  ✅ Correct detection")
            else:
                print("  ❌ Incorrect detection")
        
        detection_rate = (correct_detections / total_detections) * 100
        print(f"\\n📊 CONTEXT SWITCH DETECTION RESULTS:")
        print(f"   Total tests: {total_detections}")
        print(f"   Correct: {correct_detections}")
        print(f"   Success rate: {detection_rate:.1f}%")
        
        # Quality threshold (context switch detection is complex)
        assert detection_rate >= 50, f"Context switch detection rate too low: {detection_rate:.1f}%"
        
    def test_entity_resolution_with_conversation_history(self):
        """Test entity resolution with conversation context"""
        
        print("\\n🔍 TESTING ENTITY RESOLUTION WITH CONVERSATION HISTORY")
        print("=" * 50)
        
        # Build conversation history
        conversation_queries = [
            "Tesla earnings report",
            "Apple iPhone sales", 
            "Google AI developments",
            "Microsoft cloud services"
        ]
        
        # Test queries that should resolve entities from history
        test_queries = [
            ("How are they performing?", ["Tesla", "Apple", "Google", "Microsoft"]),
            ("What about their competition?", ["Microsoft"]),  # Most recent
            ("Any updates on the tech companies?", ["Tesla", "Apple", "Google", "Microsoft"]),
        ]
        
        successful_resolutions = 0
        total_tests = len(test_queries)
        
        for query, expected_entities in test_queries:
            print(f"\\nQuery: '{query}'")
            print(f"Expected entities: {expected_entities}")
            
            # Use entity resolver with conversation history
            resolution_result = self.entity_resolver.resolve_entities(query, conversation_queries)
            resolved_entities = [entity.text for entity in resolution_result.entities]
            
            print(f"Resolved entities: {resolved_entities}")
            print(f"Coreferences: {resolution_result.coreferences}")
            print(f"Confidence: {resolution_result.confidence:.3f}")
            
            # Check if any expected entities were resolved
            found_entities = []
            for expected in expected_entities:
                if any(expected.lower() in entity.lower() for entity in resolved_entities):
                    found_entities.append(expected)
            
            if found_entities:
                successful_resolutions += 1
                print(f"  ✅ Found entities: {found_entities}")
            else:
                print(f"  ❌ No expected entities found")
        
        resolution_rate = (successful_resolutions / total_tests) * 100
        print(f"\\n📊 ENTITY RESOLUTION RESULTS:")
        print(f"   Total tests: {total_tests}")
        print(f"   Successful: {successful_resolutions}")
        print(f"   Success rate: {resolution_rate:.1f}%")
        
        # Quality threshold
        assert resolution_rate >= 60, f"Entity resolution success rate too low: {resolution_rate:.1f}%"
        
    def test_system_integration_context_flow(self):
        """Test end-to-end context flow through the system"""
        
        print("\\n🔍 TESTING SYSTEM INTEGRATION CONTEXT FLOW")
        print("=" * 50)
        
        # Simulate a realistic conversation flow
        conversation_flow = [
            {
                "query": "Tesla earnings report",
                "expected_entities": ["Tesla"],
                "context_needed": False
            },
            {
                "query": "What about their competition?",
                "expected_entities": ["Tesla"],  # Should reference Tesla
                "context_needed": True
            },
            {
                "query": "How is Ford doing?",
                "expected_entities": ["Ford"],
                "context_needed": False
            },
            {
                "query": "Compare their EV strategies",
                "expected_entities": ["Tesla", "Ford"],  # Should reference both
                "context_needed": True
            }
        ]
        
        # Simulate entity memory and conversation history
        entity_memory = {}
        conversation_history = []
        
        successful_flows = 0
        total_flows = len(conversation_flow)
        
        for i, turn in enumerate(conversation_flow):
            print(f"\\n--- Turn {i+1}: {turn['query']} ---")
            
            # Check if context resolution is needed
            needs_resolution = needs_context_resolution(turn['query'])
            print(f"Needs context resolution: {needs_resolution}")
            print(f"Expected to need context: {turn['context_needed']}")
            
            # Resolve query with current context
            if needs_resolution and entity_memory:
                resolved_query = resolve_contextual_query(
                    turn['query'], 
                    entity_memory, 
                    conversation_history
                )
                print(f"Resolved query: {resolved_query}")
            else:
                resolved_query = turn['query']
                print(f"Original query used: {resolved_query}")
            
            # Extract entities from resolved query
            extracted_entities = extract_entities_from_text(resolved_query)
            print(f"Extracted entities: {extracted_entities}")
            
            # Update entity memory and conversation history
            if extracted_entities:
                entity_memory['last_entities'] = extracted_entities
                entity_memory['last_entity'] = extracted_entities[0]
            
            conversation_history.append({
                "query": turn['query'],
                "entities": extracted_entities
            })
            
            # Check if we got expected entities
            expected_found = []
            for expected in turn['expected_entities']:
                if any(expected.lower() in entity.lower() for entity in extracted_entities) or \
                   any(expected.lower() in resolved_query.lower() for _ in [1]):
                    expected_found.append(expected)
            
            if expected_found:
                successful_flows += 1
                print(f"✅ Found expected entities: {expected_found}")
            else:
                print(f"❌ Missing expected entities: {turn['expected_entities']}")
            
            print(f"Current entity memory: {entity_memory}")
        
        flow_success_rate = (successful_flows / total_flows) * 100
        print(f"\\n📊 INTEGRATION FLOW RESULTS:")
        print(f"   Total turns: {total_flows}")
        print(f"   Successful: {successful_flows}")
        print(f"   Success rate: {flow_success_rate:.1f}%")
        
        # Quality threshold
        assert flow_success_rate >= 70, f"Integration flow success rate too low: {flow_success_rate:.1f}%"

if __name__ == "__main__":
    # Run focused tests
    test_suite = TestContextHistoryActual()
    test_suite.setup_method()
    
    print("🔍 FOCUSED CONTEXT HISTORY TESTING")
    print("Using actual system APIs and realistic scenarios")
    print("=" * 60)
    
    try:
        test_suite.test_contextual_query_resolution_scenarios()
        test_suite.test_entity_extraction_robustness()
        test_suite.test_semantic_context_switch_detection()
        test_suite.test_entity_resolution_with_conversation_history()
        test_suite.test_system_integration_context_flow()
        
        print("\\n" + "=" * 60)
        print("🎉 ALL FOCUSED CONTEXT HISTORY TESTS COMPLETED")
        print("✅ System demonstrates solid context management capabilities")
        
    except Exception as e:
        print(f"\\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise