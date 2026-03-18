"""
Main orchestrator that coordinates LLM router with graph execution.
Entry point for the enhanced NewsIQ system.
"""

import asyncio
from intelligent_router import IntelligentRouter
from graph.builder import graph
from memory.checkpointer import get_thread_config

class NewsIQOrchestrator:
    def __init__(self):
        self.router = IntelligentRouter()
        self.conversation_memory = {}
    
    async def process_query(self, user_query: str, thread_id: str = "default"):
        """Main entry point - routes query through LLM or graph."""
        
        # Get conversation memory for this thread
        memory = self.conversation_memory.get(thread_id, {})
        
        # Route the query
        decision = self.router.route_query(user_query, memory)
        
        if decision.action == "direct_response":
            # Handle directly without graph
            if "what can you do" in user_query.lower() or "capabilities" in user_query.lower():
                response = self.router.get_system_capabilities()
            else:
                response = decision.response or "I'm here to help with news analysis and current events."
            self._update_memory(thread_id, user_query, response, direct=True)
            
        else:
            # Delegate to graph pipeline
            graph_query = decision.graph_query or user_query
            
            state = {
                'user_query': graph_query,
                'thread_id': thread_id,
                'messages': [],
                'entity_memory': memory.get('entity_memory', {}),
                'session_cache': {},
                'step_outputs': {},
                'prior_entity_results': []
            }
            
            result = await graph.ainvoke(state, get_thread_config(thread_id))
            response = result.get('final_answer', 'No response generated.')
            
            # Update memory with graph results
            self._update_memory(thread_id, user_query, response, 
                              entity_memory=result.get('entity_memory', {}))
        
        return {
            'response': response,
            'routing_decision': decision.action,
            'reasoning': decision.reasoning,
            'thread_id': thread_id
        }
    
    def _update_memory(self, thread_id: str, query: str, response: str, 
                      entity_memory: dict = None, direct: bool = False):
        """Update conversation memory."""
        if thread_id not in self.conversation_memory:
            self.conversation_memory[thread_id] = {}
        
        memory = self.conversation_memory[thread_id]
        memory['last_query'] = query
        memory['last_response'] = response[:200] + "..." if len(response) > 200 else response
        
        if entity_memory:
            memory['entity_memory'] = entity_memory
            memory['last_entities'] = entity_memory.get('last_entities', [])
            memory['last_topic'] = entity_memory.get('last_entity', '')
        
        memory['conversation_context'] = "direct_response" if direct else "news_analysis"

# Global orchestrator instance
orchestrator = NewsIQOrchestrator()