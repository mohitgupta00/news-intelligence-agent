import streamlit as st
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.builder import graph
from memory.checkpointer import get_thread_config
from tools.fetch_news import clear_cache

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

def init_session():
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'state' not in st.session_state:
        st.session_state.state = get_initial_state()

def process_query(query: str) -> str:
    state = st.session_state.state
    
    state['user_query'] = query
    
    config = get_thread_config(st.session_state.thread_id)
    
    result = graph.invoke(state, config)
    
    st.session_state.state = result
    
    if result.get('messages'):
        for msg in result['messages']:
            st.session_state.history.append({
                'role': msg.get('role', 'assistant'),
                'content': msg.get('content', '')
            })
    
    return result.get('final_answer', 'I apologize, but I could not generate a response.')

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
        if st.button("Clear Conversation"):
            st.session_state.history = []
            st.session_state.state = get_initial_state()
            st.session_state.thread_id = str(uuid.uuid4())
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Sources")
        st.markdown("- **NewsAPI** (primary)")
        st.markdown("- NewsData.io (fallback)")
        st.markdown("- GNews (fallback)")
        st.markdown("- GDELT (timelines)")
        
        st.markdown("---")
        st.markdown("### Model")
        st.markdown("- **Groq** - Planning/Replanning")
        st.markdown("- **Gemini** - Analysis")
    
    for msg in st.session_state.history:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
    
    if prompt := st.chat_input("Ask about any news topic..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Researching..."):
                response = process_query(prompt)
                st.markdown(response)
                st.session_state.history.append({
                    'role': 'assistant',
                    'content': response
                })

if __name__ == "__main__":
    main()
