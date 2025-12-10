import streamlit as st
import queue
import time
import json
import pandas as pd
import sys
import os

# Ensure project root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui._worker import Worker
from ui._render import render_terminal_line, render_agent_card, render_timeline
from ui._schema import PartialEvent

st.set_page_config(page_title="Diplomatic War Room", layout="wide", page_icon="🌍")

# Custom CSS for "War Room" aesthetic
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    h1, h2, h3 { color: #d29922; border-bottom: 2px solid #d29922; padding-bottom: 5px; }
    .stButton>button { border: 1px solid #d29922; color: #d29922; background-color: transparent; }
    .stButton>button:hover { background-color: #d29922; color: black; }
    .terminal-box { 
        background-color: #000; color: #0f0; 
        font-family: 'Fira Code', 'Courier New', monospace; 
        padding: 10px; border-radius: 5px; 
        height: 400px; overflow-y: auto; border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

st.title("DIPLOMATIC STRATEGIC SIMULATION TERMINAL // CLASSIFIED")

# Session State Initialization
if "queue" not in st.session_state:
    st.session_state["queue"] = queue.Queue()
if "terminal_logs" not in st.session_state:
    st.session_state["terminal_logs"] = []
if "control" not in st.session_state:
    st.session_state["control"] = {"paused": False, "stop": False}
if "simulation_data" not in st.session_state:
    st.session_state["simulation_data"] = {}
if "timeline_data" not in st.session_state:
    st.session_state["timeline_data"] = []
if "worker" not in st.session_state:
    st.session_state["worker"] = None
if "final_result" not in st.session_state:
    st.session_state["final_result"] = None

# Sidebar: Mission Control
with st.sidebar:
    st.header("Mission Control")
    st.markdown("---")
    
    # Inputs
    actor_a = st.text_input("Actor A (Focal)", "Union of Pacific States")
    actor_b = st.text_input("Actor B (Rival)", "Eurasian Hegemony")
    actor_c = st.text_input("Actor C (Neutral)", "Non-Aligned Alliance")
    global_context = st.text_area("Global Intelligence", "Global energy crisis. High inflation. Rising geopolitical tensions.")
    
    st.markdown("---")
    
    # Run Button
    if st.button("COMMENCE SIMULATION", type="primary"):
        # Reset State
        st.session_state["terminal_logs"] = []
        st.session_state["timeline_data"] = []
        st.session_state["final_result"] = None
        st.session_state["simulation_data"] = {}
        st.session_state["control"] = {"paused": False, "stop": False}
        
        # Build Request
        context = {
            "actors": {"A": actor_a, "B": actor_b, "C": actor_c},
            "strategies": {},
            "max_turns": 5
        }
        request_text = f"Analyze stability given: {global_context}"
        
        # Start Worker
        q = queue.Queue()
        st.session_state["queue"] = q
        worker = Worker(q, request_text, context, st.session_state["control"])
        worker.start()
        st.session_state["worker"] = worker
        st.rerun()

    # Controls during run
    if st.session_state["worker"] and st.session_state["worker"].is_alive():
        col1, col2 = st.columns(2)
        if col1.button("PAUSE" if not st.session_state["control"]["paused"] else "RESUME"):
            st.session_state["control"]["paused"] = not st.session_state["control"]["paused"]
            st.rerun()
        if col2.button("ABORT"):
            st.session_state["control"]["stop"] = True
            st.session_state["worker"] = None
            st.rerun()

# Main Layout
col_main, col_right = st.columns([2, 1])

# Event Loop Processing
if st.session_state["worker"] and st.session_state["worker"].is_alive():
    try:
        # Poll queue
        msg = st.session_state["queue"].get_nowait()
        
        if msg["type"] == "progress":
            st.session_state["progress"] = msg["value"]
            st.toast(msg["text"], icon="ℹ️")
            
        elif msg["type"] == "turn":
            st.session_state["terminal_logs"].append(msg["payload"])
            
        elif msg["type"] == "card_update":
            st.session_state["simulation_data"][msg["agent"]] = msg["content"]
            
        elif msg["type"] == "timeline_update":
            st.session_state["timeline_data"].append(msg["turn"])
            
        elif msg["type"] == "done":
            st.session_state["final_result"] = msg["payload"]
            st.session_state["worker"] = None # Stop polling
            st.success("Mission Complete")
            
        elif msg["type"] == "error":
            st.error(f"Critical Failure: {msg['payload']}")
            with st.expander("Traceback"):
                st.code(msg["trace"])
            st.session_state["worker"] = None

        st.rerun() # Immediate rerun to process next event quickly
            
    except queue.Empty:
        time.sleep(0.1) # Wait a bit then rerun to check queue again
        st.rerun()

# Render UI
with col_main:
    st.subheader("Tactical Terminal")
    
    # Terminal Output
    terminal_html = "".join([render_terminal_line(line) for line in st.session_state["terminal_logs"]])
    st.markdown(f'<div class="terminal-box">{terminal_html}</div>', unsafe_allow_html=True)
    
    # Timeline
    st.subheader("Strategic Timeline")
    render_timeline(st.session_state["timeline_data"])
    
    if st.session_state["final_result"]:
        st.subheader("Executive Summary")
        st.info(st.session_state["final_result"].get("manager_report", "No report generated."))

with col_right:
    st.subheader("Agent Network")
    
    # Render Agents Cards
    security_data = st.session_state["simulation_data"].get("security", "Standby...")
    render_agent_card("SECURITY", "Active", security_data[:200] + "...", "red")
    
    tech_data = st.session_state["simulation_data"].get("technology", "Standby...")
    render_agent_card("TECHNOLOGY", "Active", tech_data[:200] + "...", "blue")
    
    econ_data = st.session_state["simulation_data"].get("economics", "Standby...")
    render_agent_card("ECONOMICS", "Active", econ_data[:200] + "...", "green")

