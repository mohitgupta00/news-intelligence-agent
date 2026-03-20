"""
Main orchestrator that coordinates LLM router with graph execution.
Entry point for the enhanced NewsIQ system.
"""

import asyncio
import logging
import time
from intelligent_router import IntelligentRouter
from graph.builder import graph
from memory.checkpointer import get_thread_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsIQOrchestrator:
    def __init__(self):
        self.router = IntelligentRouter()
        self.conversation_memory = {}
    
    def _create_complete_graph_state(self, query: str, thread_id: str, memory: dict) -> dict:
        """Create complete graph state with all required fields."""
        # Build conversation history from memory
        conversation_history = []
        if memory:
            if memory.get('last_query') and memory.get('last_entities'):
                conversation_history.append({
                    'query': memory['last_query'],
                    'entities': memory['last_entities']
                })
        
        return {
            'user_query': query,
            'thread_id': thread_id,
            'messages': [],
            'resolved_query': '',
            'api_queries': [],
            'intent': '',
            'temporal_constraint': None,
            
            # Enhanced tracking
            'active_entities': [],
            'search_queries': [],
            'query_resolution': None,
            'context_hints': None,
            'extracted_entities': [],
            
            'plan': [],
            'current_step': 0,
            'step_outputs': {},
            'planning_done': False,
            'conversation_history': conversation_history,
            'entity_memory': {
                'last_entity': None,
                'last_entities': [],
                'last_task': None,
                'last_result': None,
                'current_entities': [],
                **memory.get('entity_memory', {})
            },
            'prior_entity_results': [],
            'session_cache': {},
            'replan_count': 0,
            'replan_decision': None,
            'final_answer': None,
            'processing_stats': {}
        }
    
    async def process_query(self, user_query: str, thread_id: str = "default"):
        """Main entry point - single-pass routing with context resolution."""
        logger.info(f"Processing query for thread {thread_id}: '{user_query[:50]}...'")
        
        # Get conversation memory for this thread
        memory = self.conversation_memory.get(thread_id, {})
        context_summary = memory.get('context_summary', '')
        logger.debug(f"Retrieved context summary: '{context_summary}'")
        
        # Single-pass routing and context resolution
        start_time = time.time()
        try:
            decision = await self.router.resolve_intent_and_context(user_query, context_summary)
            routing_time = time.time() - start_time
            
            logger.info(f"Single-pass resolution: {decision.routing} (confidence: {decision.confidence:.2f}, took {routing_time:.3f}s)")
            
            # Fallback safety layer
            if decision.confidence < 0.7:
                logger.warning(f"Low confidence ({decision.confidence:.2f}), using fallback")
                decision.resolved_query = user_query  # Use original query
                decision.confidence = 0.6
            
            # Update memory with new context summary
            self._update_memory_with_summary(thread_id, user_query, decision.updated_summary)
            
        except Exception as e:
            logger.error(f"Single-pass resolution failed: {e}")
            # Complete fallback to legacy routing
            legacy_decision = self.router.route_query(user_query, memory)
            decision = type('obj', (object,), {
                'routing': legacy_decision.action,
                'resolved_query': legacy_decision.graph_query or user_query,
                'confidence': legacy_decision.routing_confidence or 0.6,
                'updated_summary': context_summary or f"Discussing {user_query[:30]}"
            })()
            routing_time = time.time() - start_time
        
        if decision.routing == "direct_response":
            logger.info("Handling query directly without graph execution")
            if "what can you do" in user_query.lower() or "capabilities" in user_query.lower():
                response = self.router.get_system_capabilities()
            else:
                response = "I'm here to help with news analysis and current events."
            
            self._update_memory(thread_id, user_query, response, direct=True)
            
        else:
            logger.info("Delegating to graph pipeline for analysis")
            # Use resolved query for graph processing
            graph_query = decision.resolved_query
            logger.debug(f"Graph query: '{graph_query}'")
            
            # Create state with resolved query and context
            state = self._create_complete_graph_state(graph_query, thread_id, memory)
            state['context_summary'] = decision.updated_summary
            state['resolution_confidence'] = decision.confidence
            
            try:
                graph_start_time = time.time()
                result = await graph.ainvoke(state, get_thread_config(thread_id))
                graph_execution_time = time.time() - graph_start_time
                
                logger.info(f"Graph execution completed in {graph_execution_time:.3f}s")
                
                response = result.get('final_answer')
                if not response or not isinstance(response, str) or response.strip() == "":
                    logger.warning("Graph returned empty final_answer")
                    response = "I couldn't generate a proper response for your news query. Please try rephrasing your question."
                
                # Update memory with graph results
                self._update_memory(thread_id, user_query, response, 
                                  entity_memory=result.get('entity_memory', {}))
                                  
            except Exception as graph_error:
                logger.error(f"Graph execution failed: {graph_error}")
                response = "I'm experiencing technical difficulties processing your news query. Please try again later."
                self._update_memory(thread_id, user_query, response, direct=True)
        
        total_time = time.time() - start_time
        logger.info(f"Query processing completed in {total_time:.3f}s")
        
        return {
            'response': response,
            'routing_decision': decision.routing,
            'reasoning': f"Single-pass resolution (confidence: {decision.confidence:.2f})",
            'resolved_query': decision.resolved_query,
            'original_query': user_query,
            'context_summary': decision.updated_summary,
            'thread_id': thread_id,
            'processing_time': total_time,
            'routing_time': routing_time,
            'fallback_used': decision.confidence < 0.7
        }
    
    def _should_reset_summary(self, memory: dict) -> bool:
        """Check if context summary should be reset due to expiration or drift."""
        # Reset after 10 minutes of inactivity
        last_update = memory.get('last_update', 0)
        if time.time() - last_update > 600:  # 10 minutes
            return True
        
        # Reset if context summary becomes too long (indicates drift)
        summary = memory.get('context_summary', '')
        if len(summary) > 100:
            return True
        
        return False
    
    def _update_memory_with_summary(self, thread_id: str, query: str, context_summary: str):
        """Update conversation memory with context summary."""
        if thread_id not in self.conversation_memory:
            self.conversation_memory[thread_id] = {}
        
        memory = self.conversation_memory[thread_id]
        
        # Check if summary should be reset
        if self._should_reset_summary(memory):
            logger.info(f"Resetting context summary for thread {thread_id} (expiration/drift)")
            context_summary = f"Discussing {query[:30]}"  # Fresh start
        
        memory['last_query'] = query
        memory['context_summary'] = context_summary
        memory['last_update'] = time.time()
    
    def _update_memory(self, thread_id: str, query: str, response: str, 
                      entity_memory: dict = None, direct: bool = False):
        """Update conversation memory."""
        if thread_id not in self.conversation_memory:
            self.conversation_memory[thread_id] = {}
        
        memory = self.conversation_memory[thread_id]
        memory['last_query'] = query
        
        # Safe response handling
        if response and isinstance(response, str):
            memory['last_response'] = response[:200] + "..." if len(response) > 200 else response
        else:
            memory['last_response'] = "No response generated"
        
        # Safe entity memory handling
        if entity_memory and isinstance(entity_memory, dict):
            memory['entity_memory'] = entity_memory
            memory['last_entities'] = entity_memory.get('last_entities', [])
            memory['last_topic'] = entity_memory.get('last_entity', '')
        
        memory['conversation_context'] = "direct_response" if direct else "news_analysis"
        memory['last_update'] = time.time()

# Global orchestrator instance
orchestrator = NewsIQOrchestrator()