"""
Simple helper for rolling summaries of simulation turns.
"""
from typing import List, Optional

def update_summary(existing_summary: str, recent_turns: List[str]) -> str:
    """
    Updates the rolling summary with new turns.
    In a real implementation, this would call an LLM.
    For now, we append concisely to avoid infinite growth in a naive way,
    or just return the concatenation if small.
    
    Args:
        existing_summary: The previous summary text.
        recent_turns: List of string representations of new turns.
        
    Returns:
        New summary string.
    """
    # Naive implementation for demo purposes:
    # If summary is too long, we might want to truncate or placeholder.
    # In full version: call a fast LLM to condense.
    
    new_content = "\n".join(recent_turns)
    if not existing_summary:
        return new_content
        
    return f"{existing_summary}\n{new_content}"

def format_turn(turn_idx: int, actor: str, action: str) -> str:
    return f"Turn {turn_idx} [{actor}]: {action}"
