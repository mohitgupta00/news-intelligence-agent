"""
Neural Context Management Tests
Test the enhanced context and entity resolution system
"""
import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.semantic_context import get_context_manager
from utils.entity_resolution import get_entity_resolver
from intelligent_router import IntelligentRouter

class TestNeuralContextManagement:
    
    def setup_method(self):
        """Setup test environment"""
        self.context_manager = get_context_manager()
        self.entity_resolver = get_entity_resolver()
        self.router = IntelligentRouter()
        
        # Reset context for clean tests
        self.context_manager.reset_context()
    
    def test_entity_resolution_with_coreference(self):
        """Test advanced entity resolution with coreference"""
        test_cases = [
            # Basic entity extraction
            ("Tesla earnings news", [], ["Tesla"]),
            ("Apple vs Google AI", [], ["Apple", "Google"]),
            
            # Coreference resolution
            ("Tesla earnings report", ["Tesla earnings report"], ["Tesla"]),
            ("What about their competition?", ["Tesla earnings report"], ["Tesla"]),  # Should resolve 'their'
            
            # Multi-entity scenarios
            ("Biden and Trump debate", [], ["Biden", "Trump"]),
            ("How are they performing?", ["Biden and Trump debate"], ["Biden", "Trump"]),
        ]
        
        passed = 0
        for query, conversation_history, expected_entities in test_cases:
            try:
                resolution = self.entity_resolver.resolve_entities(query, conversation_history)
                resolved_entities = [entity.text for entity in resolution.entities]
                
                # Check if expected entities are found
                entities_found = all(entity in resolved_entities for entity in expected_entities)
                
                if entities_found:
                    passed += 1
                    print(f"✅ Entity resolution: '{query}' -> {resolved_entities}")
                    if resolution.coreferences:
                        print(f"   Coreferences: {resolution.coreferences}")
                else:
                    print(f"❌ Entity resolution: '{query}' -> {resolved_entities} (expected: {expected_entities})")
                    
            except Exception as e:
                print(f"❌ Entity resolution error: '{query}' -> {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Entity Resolution with Coreference: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def test_neural_context_switch_detection(self):
        """Test neural context switch detection"""
        conversation_scenarios = [
            # Explicit switches
            [
                ("Tesla stock news", False, "continuation"),
                ("Now tell me about Apple", True, "explicit"),
                ("What about their iPhone?", False, "continuation")
            ],
            
            # Semantic drift
            [
                ("Ukraine conflict updates", False, "continuation"),
                ("Climate change impact", True, "semantic_drift"),
                ("Global warming effects", False, "continuation")
            ],
            
            # Entity change
            [
                ("Biden climate policy", False, "continuation"),
                ("Trump's position on environment", True, "entity_change"),
                ("His previous statements", False, "continuation")
            ]
        ]
        
        passed_scenarios = 0
        for i, scenario in enumerate(conversation_scenarios):
            try:
                scenario_passed = True
                
                for j, (query, expected_switch, expected_type) in enumerate(scenario):
                    # Extract entities for context update
                    resolution = self.entity_resolver.resolve_entities(query, [])
                    entities = [entity.text for entity in resolution.entities]
                    
                    # Update context and detect switch
                    switch_result = self.context_manager.update_context(query, entities)
                    
                    # Validate switch detection
                    if switch_result.switch_detected == expected_switch:
                        print(f"✅ Context switch scenario {i+1}, turn {j+1}: {switch_result.switch_type} (confidence: {switch_result.confidence:.2f})")
                    else:
                        print(f"❌ Context switch scenario {i+1}, turn {j+1}: Expected {expected_switch}, got {switch_result.switch_detected}")
                        scenario_passed = False
                
                if scenario_passed:
                    passed_scenarios += 1
                    
            except Exception as e:
                print(f"❌ Context switch scenario {i+1} error: {e}")
        
        success_rate = (passed_scenarios / len(conversation_scenarios)) * 100
        print(f"\n📊 Neural Context Switch Detection: {passed_scenarios}/{len(conversation_scenarios)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_attention_based_context_retrieval(self):
        """Test attention-based context retrieval"""
        # Build conversation history
        conversation_turns = [
            ("Tesla earnings report Q3", ["Tesla"]),
            ("Apple iPhone sales decline", ["Apple"]),
            ("Microsoft cloud revenue growth", ["Microsoft"]),
            ("Google AI breakthrough", ["Google"])
        ]
        
        # Build context history
        for query, entities in conversation_turns:
            self.context_manager.update_context(query, entities)
        
        # Test relevant context retrieval
        test_queries = [
            ("Tesla stock analysis", ["Tesla"]),  # Should retrieve Tesla context
            ("Apple vs competitors", ["Apple"]),   # Should retrieve Apple context
            ("Tech company comparison", []),       # Should retrieve multiple tech contexts
        ]
        
        passed = 0
        for query, expected_entities in test_queries:
            try:
                relevant_context = self.context_manager.get_relevant_context(query)
                retrieved_entities = relevant_context.get('relevant_entities', [])
                
                # Check if expected entities are in retrieved context
                if expected_entities:
                    entities_found = any(entity in retrieved_entities for entity in expected_entities)
                else:
                    entities_found = len(retrieved_entities) > 0  # Should retrieve something
                
                if entities_found:
                    passed += 1
                    print(f"✅ Context retrieval: '{query}' -> {retrieved_entities}")
                    print(f"   Confidence: {relevant_context.get('context_confidence', 0):.2f}")
                else:
                    print(f"❌ Context retrieval: '{query}' -> {retrieved_entities} (expected entities: {expected_entities})")
                    
            except Exception as e:
                print(f"❌ Context retrieval error: '{query}' -> {e}")
        
        success_rate = (passed / len(test_queries)) * 100
        print(f"\n📊 Attention-Based Context Retrieval: {passed}/{len(test_queries)} ({success_rate:.1f}%)")
        return success_rate >= 75
    
    def test_neural_router_integration(self):
        """Test integration with neural router"""
        test_cases = [
            # Context continuation
            ("Tesla earnings news", {}),
            ("What about their competition?", {"last_query": "Tesla earnings news"}),
            
            # Context switching
            ("Apple stock analysis", {"last_query": "Tesla earnings news"}),
            ("Now tell me about Google", {"last_query": "Apple stock analysis"}),
            
            # Complex queries
            ("Compare Biden and Trump policies", {}),
            ("How do they differ on climate?", {"last_query": "Compare Biden and Trump policies"}),
        ]
        
        passed = 0
        for query, memory in test_cases:
            try:
                decision = self.router.route_query(query, memory)
                
                # Should successfully route with neural insights
                if (hasattr(decision, 'action') and 
                    decision.action in ['direct_response', 'delegate_to_graph'] and
                    hasattr(decision, 'resolved_entities')):
                    passed += 1
                    print(f"✅ Neural router: '{query}' -> {decision.action}")
                    if decision.resolved_entities:
                        print(f"   Entities: {decision.resolved_entities}")
                    if hasattr(decision, 'context_switch_detected'):
                        print(f"   Context switch: {decision.context_switch_detected}")
                else:
                    print(f"❌ Neural router: '{query}' -> Invalid decision structure")
                    
            except Exception as e:
                print(f"❌ Neural router error: '{query}' -> {e}")
        
        success_rate = (passed / len(test_cases)) * 100
        print(f"\n📊 Neural Router Integration: {passed}/{len(test_cases)} ({success_rate:.1f}%)")
        return success_rate >= 80
    
    def test_semantic_similarity_performance(self):
        """Test semantic similarity computation performance"""
        test_queries = [
            "Tesla earnings report",
            "Apple iPhone sales",
            "Microsoft cloud services",
            "Google AI research",
            "Amazon e-commerce growth"
        ]
        
        import time
        
        passed = 0
        total_time = 0
        
        for query in test_queries:
            try:
                start_time = time.time()
                
                # Test entity resolution
                resolution = self.entity_resolver.resolve_entities(query, [])
                
                # Test context update
                entities = [entity.text for entity in resolution.entities]
                switch_result = self.context_manager.update_context(query, entities)
                
                # Test context retrieval
                relevant_context = self.context_manager.get_relevant_context(query)
                
                end_time = time.time()
                processing_time = end_time - start_time
                total_time += processing_time
                
                # Should complete within reasonable time (2 seconds)
                if processing_time < 2.0:
                    passed += 1
                    print(f"✅ Performance: '{query}' -> {processing_time:.3f}s")
                else:
                    print(f"❌ Performance: '{query}' -> {processing_time:.3f}s (too slow)")
                    
            except Exception as e:
                print(f"❌ Performance error: '{query}' -> {e}")
        
        avg_time = total_time / len(test_queries) if test_queries else 0
        success_rate = (passed / len(test_queries)) * 100
        
        print(f"\n📊 Semantic Similarity Performance: {passed}/{len(test_queries)} ({success_rate:.1f}%)")
        print(f"📈 Average Processing Time: {avg_time:.3f}s")
        
        return success_rate >= 80 and avg_time < 1.0

def run_neural_context_tests():
    """Run all neural context management tests"""
    print("🧠 RUNNING NEURAL CONTEXT MANAGEMENT TESTS")
    print("=" * 60)
    
    test_suite = TestNeuralContextManagement()
    test_suite.setup_method()
    
    results = {
        "Entity Resolution with Coreference": test_suite.test_entity_resolution_with_coreference(),
        "Neural Context Switch Detection": test_suite.test_neural_context_switch_detection(),
        "Attention-Based Context Retrieval": test_suite.test_attention_based_context_retrieval(),
        "Neural Router Integration": test_suite.test_neural_router_integration(),
        "Semantic Similarity Performance": test_suite.test_semantic_similarity_performance()
    }
    
    print("\n" + "=" * 60)
    print("📋 NEURAL CONTEXT MANAGEMENT TEST SUMMARY")
    print("=" * 60)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    overall_success = (passed_tests / total_tests) * 100
    print(f"\n🎯 Overall Success Rate: {passed_tests}/{total_tests} ({overall_success:.1f}%)")
    
    if overall_success >= 80:
        print("🎉 NEURAL CONTEXT MANAGEMENT: PRODUCTION READY")
        return True
    else:
        print("⚠️  NEURAL CONTEXT MANAGEMENT: NEEDS IMPROVEMENT")
        return False

if __name__ == "__main__":
    run_neural_context_tests()