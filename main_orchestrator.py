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
        """Main entry point - routes query through LLM or graph."""
        logger.info(f"Processing query for thread {thread_id}: '{user_query[:50]}...'")
        
        # Get conversation memory for this thread
        memory = self.conversation_memory.get(thread_id, {})
        logger.debug(f"Retrieved memory for thread {thread_id}: {len(memory)} items")
        
        # Route the query
        start_time = time.time()
        decision = self.router.route_query(user_query, memory)
        routing_time = time.time() - start_time
        
        logger.info(f"Router decision: {decision.action} (took {routing_time:.3f}s)")
        logger.debug(f"Router reasoning: {decision.reasoning}")
        
        if decision.action == "direct_response":
            logger.info("Handling query directly without graph execution")
            # Handle directly without graph
            if "what can you do" in user_query.lower() or "capabilities" in user_query.lower():
                response = self.router.get_system_capabilities()
                logger.debug("Returned system capabilities")
            else:
                response = decision.response or "I'm here to help with news analysis and current events."
                logger.debug(f"Direct response length: {len(response)} chars")
            self._update_memory(thread_id, user_query, response, direct=True)
            
        else:
            logger.info("Delegating to graph pipeline for analysis")
            # Delegate to graph pipeline with router insights
            graph_query = decision.graph_query or user_query
            logger.debug(f"Graph query: '{graph_query}'")
            
            # Create context hints from router insights
            context_hints = {
                "resolved_entities": decision.resolved_entities,
                "resolved_topic": decision.resolved_topic,
                "routing_confidence": decision.routing_confidence,
                "suggested_sources": decision.suggested_sources
            }
            
            # FIX: Use complete state initialization with router context
            state = self._create_complete_graph_state(graph_query, thread_id, memory)
            state['context_hints'] = context_hints
            logger.debug(f"Created graph state with router context hints: {context_hints}")
            
            try:
                graph_start_time = time.time()
                result = await graph.ainvoke(state, get_thread_config(thread_id))
                graph_execution_time = time.time() - graph_start_time
                
                logger.info(f"Graph execution completed in {graph_execution_time:.3f}s")
                
                # Validate graph result
                if not result or not isinstance(result, dict):
                    logger.error("Graph returned invalid result structure")
                    raise ValueError("Invalid graph result structure")
                
                response = result.get('final_answer')
                if not response or not isinstance(response, str) or response.strip() == "":
                    logger.warning("Graph returned empty or invalid final_answer")
                    response = "I couldn't generate a proper response for your news query. Please try rephrasing your question."
                
                logger.debug(f"Final response length: {len(response)} chars")
                
                # Update memory with graph results
                self._update_memory(thread_id, user_query, response, 
                                  entity_memory=result.get('entity_memory', {}))
                                  
            except Exception as graph_error:
                logger.error(f"Graph execution failed for query '{user_query}': {graph_error}")
                
                # User-friendly error messages based on error type
                if "timeout" in str(graph_error).lower():
                    response = "I'm taking longer than usual to process your request. Please try a more specific query or try again later."
                elif "api" in str(graph_error).lower() or "network" in str(graph_error).lower():
                    response = "I'm having trouble accessing news sources right now. Please try again in a few moments."
                elif "rate limit" in str(graph_error).lower():
                    response = "I'm currently handling many requests. Please wait a moment and try again."
                else:
                    response = "I'm experiencing technical difficulties processing your news query. Please try rephrasing your question or try again later."
                
                self._update_memory(thread_id, user_query, response, direct=True)
        
        total_time = time.time() - start_time
        logger.info(f"Query processing completed in {total_time:.3f}s")
        
        return {
            'response': response,
            'routing_decision': decision.action,
            'reasoning': decision.reasoning,
            'thread_id': thread_id,
            'processing_time': total_time,
            'routing_time': routing_time
        }
    
    def _update_memory(self, thread_id: str, query: str, response: str, 
                      entity_memory: dict = None, direct: bool = False):
        """Update conversation memory."""
        if thread_id not in self.conversation_memory:
            self.conversation_memory[thread_id] = {}
        
        memory = self.conversation_memory[thread_id]
        memory['last_query'] = query
        
        # FIX: Safe response handling
        if response and isinstance(response, str):
            memory['last_response'] = response[:200] + "..." if len(response) > 200 else response
        else:
            memory['last_response'] = "No response generated"
        
        # FIX: Safe entity memory handling
        if entity_memory and isinstance(entity_memory, dict):
            memory['entity_memory'] = entity_memory
            memory['last_entities'] = entity_memory.get('last_entities', [])
            memory['last_topic'] = entity_memory.get('last_entity', '')
        
        memory['conversation_context'] = "direct_response" if direct else "news_analysis"

# Global orchestrator instance
orchestrator = NewsIQOrchestrator()