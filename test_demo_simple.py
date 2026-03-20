#!/usr/bin/env python3

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intelligent_router import IntelligentRouter

class DemoTester:
    def __init__(self):
        self.router = IntelligentRouter()
    
    async def test_pronoun_resolution(self):
        print("\n🧪 Testing Pronoun Resolution...")
        
        scenarios = [
            {
                "setup_context": "Discussing Donald Trump activities",
                "followup": "What about his Epstein connection?",
                "expected_entity": "Trump",
                "expected_topic": "Epstein"
            },
            {
                "setup_context": "Discussing Israel-Iran war updates",
                "followup": "What about this conflict?",
                "expected_entity": "Israel",
                "expected_topic": "war"
            },
            {
                "setup_context": "Comparing Apple and Google",
                "followup": "What about their AI ethics?",
                "expected_entity": "Apple",
                "expected_topic": "AI"
            }
        ]
        
        results = []
        for i, scenario in enumerate(scenarios):
            print(f"  Scenario {i+1}: {scenario['followup']}")
            
            resolution = await self.router.resolve_intent_and_context(
                scenario['followup'], scenario['setup_context']
            )
            
            resolved_query = resolution.resolved_query.lower()
            has_entity = scenario['expected_entity'].lower() in resolved_query
            has_topic = scenario['expected_topic'].lower() in resolved_query
            confidence_ok = resolution.confidence >= 0.7
            is_followup = resolution.is_contextual_follow_up
            
            success = has_entity and confidence_ok and is_followup
            results.append(success)
            
            status = "✅" if success else "❌"
            print(f"    {status} '{resolution.resolved_query}' (conf: {resolution.confidence:.2f})")
        
        success_rate = sum(results) / len(results)
        print(f"  📊 Success Rate: {success_rate:.1%}")
        return success_rate
    
    async def test_semantic_drift(self):
        print("\n🧪 Testing Semantic Drift Detection...")
        
        context = "Discussing Apple earnings report"
        drift_queries = [
            "What's the weather today?",
            "How do I bake a cake?",
            "Tell me about quantum physics"
        ]
        
        results = []
        for query in drift_queries:
            print(f"  Testing: {query}")
            
            resolution = await self.router.resolve_intent_and_context(query, context)
            drift_detected = not resolution.is_contextual_follow_up
            confidence_ok = resolution.confidence >= 0.5
            
            success = drift_detected and confidence_ok
            results.append(success)
            
            status = "✅" if success else "❌"
            print(f"    {status} Drift detected: {drift_detected} (conf: {resolution.confidence:.2f})")
        
        success_rate = sum(results) / len(results)
        print(f"  📊 Success Rate: {success_rate:.1%}")
        return success_rate
    
    async def test_fallback_activation(self):
        print("\n🧪 Testing Fallback Activation...")
        
        ambiguous_queries = [
            ("Apple news", "What about it?"),
            ("Multiple topics here", "That thing?"),
            ("", "Random query")
        ]
        
        results = []
        for context, query in ambiguous_queries:
            print(f"  Testing: '{query}' with context: '{context}'")
            
            resolution = await self.router.resolve_intent_and_context(query, context)
            has_resolved_query = bool(resolution.resolved_query.strip())
            
            success = has_resolved_query
            results.append(success)
            
            status = "✅" if success else "❌"
            fallback_status = "(fallback)" if resolution.confidence < 0.7 else "(direct)"
            print(f"    {status} Confidence: {resolution.confidence:.2f} {fallback_status}")
        
        success_rate = sum(results) / len(results)
        
        # Calculate fallback rate separately
        fallback_count = 0
        for context, query in ambiguous_queries:
            resolution = await self.router.resolve_intent_and_context(query, context)
            if resolution.confidence < 0.7:
                fallback_count += 1
        
        fallback_rate = fallback_count / len(ambiguous_queries)
        print(f"  📊 Success Rate: {success_rate:.1%}")
        print(f"  📊 Fallback Rate: {fallback_rate:.1%}")
        return success_rate
    
    async def run_all_tests(self):
        print("🚀 Starting NewsIQ Demo Validation Tests")
        start_time = time.time()
        
        pronoun_success = await self.test_pronoun_resolution()
        drift_success = await self.test_semantic_drift()
        fallback_success = await self.test_fallback_activation()
        
        overall_success = (pronoun_success + drift_success + fallback_success) / 3
        total_time = time.time() - start_time
        
        print(f"\n📊 OVERALL RESULTS:")
        print(f"  ⏱️  Total Time: {total_time:.1f}s")
        print(f"  🎯 Overall Success: {overall_success:.1%}")
        print(f"  ✅ Pronoun Resolution: {pronoun_success:.1%}")
        print(f"  ✅ Semantic Drift: {drift_success:.1%}")
        print(f"  ✅ Fallback Safety: {fallback_success:.1%}")
        
        demo_ready = overall_success >= 0.8
        print(f"\n🎭 DEMO READINESS: {'✅ READY' if demo_ready else '❌ NEEDS WORK'}")
        
        return demo_ready

async def main():
    tester = DemoTester()
    demo_ready = await tester.run_all_tests()
    sys.exit(0 if demo_ready else 1)

if __name__ == "__main__":
    asyncio.run(main())