from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

def get_thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}
