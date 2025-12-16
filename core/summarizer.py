"""
Simple helper for rolling summaries of simulation turns.
"""
from typing import List, Optional
from datetime import datetime

def update_summary(current_summary: str, new_events: List[str]) -> str:
    """
    Appends new events to the rolling summary. 
    Ideally this would be an LLM call to compress, but for now we append 
    and rely on the Simulation Agent to handle the context window.
    """
    if not new_events:
        return current_summary
        
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_events = "\n".join([f"[{timestamp}] {e}" for e in new_events])
    
    if current_summary:
        return f"{current_summary}\n{formatted_events}"
    return formatted_events

def format_turn(turn_num: int, actor: str, action: str) -> str:
    return f"Turn {turn_num} | {actor}: {action}"
