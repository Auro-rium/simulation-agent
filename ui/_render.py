import streamlit as st
import pandas as pd
import altair as alt
from typing import List, Dict, Any

def render_terminal_line(line: str) -> str:
    """Formats a log line with HTML colors based on content."""
    color = "#e0e0e0" # Default gray
    prefix = ""
    
    # Regex for timestamp [HH:MM:SS]
    import re
    time_match = re.match(r"(\[\d{2}:\d{2}:\d{2}\]) (.*)", line)
    timestamp = ""
    content = line
    if time_match:
        timestamp = time_match.group(1)
        content = time_match.group(2)

    if "[SECURITY]" in content:
        color = "#ff4b4b" # Red
        prefix = "[SECURITY]"
    elif "[TECH]" in content or "[TECHNOLOGY]" in content:
        color = "#00d4ff" # Cyan Neon
        prefix = "[TECH]"
    elif "[ECON]" in content or "[ECONOMICS]" in content:
        color = "#00ff00" # Bright Green
        prefix = "[ECON]"
    elif "[MANAGER]" in content or "[PLANNER]" in content:
        color = "#ffd700" # Gold
        prefix = "[COMMAND]"
    elif "[SIM]" in content:
        color = "#d800ff" # Magenta Neon
        prefix = "[SIM]"
    elif "[SYSTEM]" in content:
        color = "#888888"
        prefix = "[SYS]"
    
    # Strip existing brackets if any to avoid double prefixing
    clean_line = content.replace("[SECURITY]", "").replace("[TECH]", "").replace("[ECON]", "").replace("[MANAGER]", "").replace("[PLANNER]", "").replace("[SIM]", "").replace("[SYSTEM]", "")
    
    return f'''
    <div style="font-family: 'Fira Code', monospace; margin-bottom: 4px; border-left: 2px solid {color}; padding-left: 8px;">
        <span style="color: #666; font-size: 0.8em;">{timestamp}</span>
        <strong style="color: {color};">{prefix}</strong> 
        <span style="color: #e0e0e0;">{clean_line}</span>
    </div>
    '''

def render_timeline(history: List[Dict[str, Any]]):
    """Renders a timeline chart of utility/actions."""
    if not history:
        return st.info("No timeline data yet.")
        
    data = []
    for turn in history:
        # Extract utility if available, else use a placeholder score
        # Assuming the simulation turn format: {'actor': 'A', 'action': '...', 'result': '...'}
        # We'll try to parse a numeric utility or just count actions
        actor = turn.get("actor", "Unknown")
        turn_id = turn.get("turn", 0)
        
        # Simple visualization: Action occurrences
        data.append({
            "Turn": turn_id,
            "Actor": actor,
            "Action": turn.get("action", "")[:50] + "...",
            "Value": 1 # Discrete event
        })
        
    df = pd.DataFrame(data)
    
    chart = alt.Chart(df).mark_circle(size=100).encode(
        x='Turn:O',
        y='Actor:N',
        color='Actor:N',
        tooltip=['Turn', 'Actor', 'Action']
    ).properties(
        height=200,
        width='container',
        title="Simulation Timeline"
    ).interactive()
    
    st.altair_chart(chart, use_container_width=True)

def render_agent_card(name: str, status: str, details: str, color: str = "gray"):
    """Renders a styled card for an agent."""
    border_color = {
        "red": "#ff4b4b",
        "blue": "#1f77b4", 
        "green": "#2ca02c",
        "gold": "#d69e2e", 
        "gray": "#555"
    }.get(color, "#555")
    
    st.markdown(f"""
    <div style="border: 1px solid {border_color}; border-radius: 5px; padding: 10px; margin-bottom: 10px; background-color: #1e1e1e;">
        <h4 style="color: {border_color}; margin: 0;">{name}</h4>
        <p style="font-size: 0.9em; color: #ccc; margin-top: 5px;"><strong>Status:</strong> {status}</p>
        <p style="font-size: 0.8em; color: #999;">{details}</p>
    </div>
    """, unsafe_allow_html=True)
