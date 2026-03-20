import streamlit as st
import uuid
import sys
import os
import asyncio
import nest_asyncio
import time
from datetime import datetime, timedelta
nest_asyncio.apply()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.builder import graph
from memory.checkpointer import get_thread_config
from main_orchestrator import orchestrator

# Session timeout: 1 hour
SESSION_TIMEOUT_SECONDS = 3600

def get_initial_state() -> dict:
    return {
        'user_query': '',
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

def check_session_timeout():
    """Check if session has timed out (1 hour of inactivity)."""
    if 'last_activity' in st.session_state:
        elapsed = time.time() - st.session_state.last_activity
        if elapsed > SESSION_TIMEOUT_SECONDS:
            return True
    return False

def reset_session():
    """Reset session state completely."""
    st.session_state.history = []
    st.session_state.state = get_initial_state()
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.last_activity = time.time()

def init_session():
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'state' not in st.session_state:
        st.session_state.state = get_initial_state()
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = time.time()
    
    # Check for timeout
    if check_session_timeout():
        reset_session()
        st.info("⏱️ Session timed out after 1 hour of inactivity. Starting fresh.")

def process_query(query: str) -> dict:
    """Process query through orchestrator and return result with routing info."""
    result = asyncio.get_event_loop().run_until_complete(
        orchestrator.process_query(query, st.session_state.thread_id)
    )
    
    # Update last activity timestamp
    st.session_state.last_activity = time.time()
    
    return result

def main():
    st.set_page_config(
        page_title="NewsIQ - AI News Analyst",
        page_icon="📰",
        layout="wide"
    )
    
    init_session()
    
    st.title("📰 NewsIQ")
    st.markdown("AI-powered news analysis with multi-source intelligence")
    
    with st.sidebar:
        st.header("Settings")
        
        # Session info
        if st.session_state.get('last_activity'):
            elapsed = time.time() - st.session_state.last_activity
            remaining = SESSION_TIMEOUT_SECONDS - elapsed
            if remaining > 0:
                mins_remaining = int(remaining / 60)
                st.caption(f"⏱️ Session expires in: {mins_remaining} min")
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            reset_session()
            st.success("✅ Conversation cleared!")
            st.rerun()
        
        # Show conversation stats
        if st.session_state.history:
            user_msgs = len([m for m in st.session_state.history if m['role'] == 'user'])
            st.caption(f"💬 Messages: {len(st.session_state.history)} ({user_msgs} queries)")
        
        # Show active context
        entity_mem = st.session_state.state.get('entity_memory', {})
        if entity_mem.get('last_entities'):
            st.markdown("---")
            st.markdown("### 🧠 Active Context")
            st.caption(f"Topic: {', '.join(entity_mem['last_entities'][:3])}")
            if entity_mem.get('last_task'):
                st.caption(f"Last task: {entity_mem['last_task']}")
        
        # Show search memory stats
        search_stats = st.session_state.state.get('search_memory_stats', {})
        if search_stats.get('total_searches', 0) > 0:
            st.markdown("### 💾 Search Memory")
            st.caption(f"Cached searches: {search_stats['total_searches']}")
            st.caption(f"Memory usage: {search_stats['memory_size_kb']} KB")
            if st.session_state.state.get('search_memory_reused'):
                st.success("♻️ Reused previous results")
        st.markdown("---")
        st.markdown("### 📡 Sources")
        st.markdown("- **NewsAPI** (primary)")
        st.markdown("- NewsData.io (fallback)")
        st.markdown("- GNews (fallback)")
        
        st.markdown("---")
        st.markdown("### 🤖 Models")
        st.markdown("- **Groq** (llama-3.1-8b-instant)")
        st.markdown("  - Planning & Orchestration")
        st.markdown("  - Text Analysis & Summarization")
        
        st.markdown("---")
        st.markdown("### 💡 Try asking:")
        st.caption("• What is Donald Trump doing?")
        st.caption("• Then: What about his Epstein connection?")
        st.caption("• What's happening in Israel-Iran war?")
        st.caption("• Then: What is India's stance?")
    
    # Display chat history
    for msg in st.session_state.history:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
    
    # Chat input
    if prompt := st.chat_input("Ask about any news topic..."):
        # Add user message to history
        st.session_state.history.append({
            'role': 'user',
            'content': prompt
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analyzing..."):
                result = process_query(prompt)
                response = result['response']
                
                # Display response
                st.markdown(response)
                
                # Show routing decision for demo purposes
                with st.expander("🔍 System Decision (Demo Info)", expanded=False):
                    st.write(f"**Routing Decision:** {result['routing_decision']}")
                    st.write(f"**Reasoning:** {result['reasoning']}")
                    
                    # Show query transformation
                    if result.get('resolved_query') != result.get('original_query'):
                        st.write("**Query Transformation:**")
                        st.write(f"• Original: `{result.get('original_query', prompt)}`")
                        st.write(f"• Resolved: `{result['resolved_query']}`")
                    
                    # Show context summary
                    if result.get('context_summary'):
                        st.write(f"**Context Summary:** {result['context_summary']}")
                    
                    # Show fallback status
                    if result.get('fallback_used'):
                        st.warning("⚠️ Fallback safety activated (low confidence)")
                    
                    if result['routing_decision'] == 'direct_response':
                        st.success("✅ Handled directly by LLM router")
                    else:
                        st.info("🔄 Processed through graph pipeline")
                
                # Add to history
                st.session_state.history.append({
                    'role': 'assistant',
                    'content': response,
                    'routing': result['routing_decision']
                })

if __name__ == "__main__":
    main()
