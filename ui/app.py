import streamlit as st
import queue
import time
import json
import pandas as pd
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Explicitly load .env from project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)
sys.path.append(project_root)

from ui._worker import Worker
from ui import components

# Page Config
st.set_page_config(
    page_title="Strategic Operations Console",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Mode / Cyberpunk Styling
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div.block-container { padding-top: 2rem; }
    h1, h2, h3 { font-family: 'Inter', sans-serif; letter-spacing: -0.5px; }
    .stButton>button { width: 100%; border-radius: 4px; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #4caf50; }
</style>
""", unsafe_allow_html=True)

# --- State Init ---
if "queue" not in st.session_state: st.session_state["queue"] = queue.Queue()
if "timeline" not in st.session_state: st.session_state["timeline"] = []
if "worker" not in st.session_state: st.session_state["worker"] = None
if "run_state" not in st.session_state: st.session_state["run_state"] = {} # Holds the full graph state
if "control" not in st.session_state: st.session_state["control"] = {"stop": False}

# --- Sidebar: Mission Configuration ---
with st.sidebar:
    st.header("⚙️ Mission Config")
    
    # Presets
    PRESETS = {
        "Custom Scneario": {
            "ctx": "Global energy crisis. High inflation. Rising geopolitical tensions.",
            "A": "Union of Pacific States", "B": "Eurasian Hegemony", "C": "Non-Aligned Alliance"
        },
        "Tech War (2028)": {
            "ctx": "2028: AI Semiconductor Embargo Escalation. US tightens export controls. China retaliates with rare earth ban.",
            "A": "United States", "B": "China", "C": "India"
        },
        "Arctic Melt (2032)": {
            "ctx": "Arctic sea ice collapse opens Northern Sea Route. Dispute over drilling rights. Drone shot down.",
            "A": "Nordic Alliance", "B": "Eurasian Energy Bloc", "C": "Trans-Atlantic Union"
        }
    }
    
    preset = st.selectbox("Load Scenario", list(PRESETS.keys()), index=1)
    p_data = PRESETS[preset]
    
    st.subheader("Parameters")
    actor_a = st.text_input("Focal Actor (A)", value=p_data["A"])
    actor_b = st.text_input("Adversary (B)", value=p_data["B"])
    actor_c = st.text_input("Third Party (C)", value=p_data["C"])
    
    risk_tolerance = st.slider("Max Risk Tolerance", 0, 10, 8, help="Risk scores above this trigger ABORT")
    model_mode = st.radio("Inference Engine", ["Reasoned (70B)", "Fast (8B)", "Hybrid"], index=0)
    
    st.divider()
    
    if st.button("🚀 INITIATE SEQUENCE", type="primary"):
        # Reset
        st.session_state["timeline"] = []
        st.session_state["run_state"] = {}
        st.session_state["control"]["stop"] = False
        
        # Context Construction
        context = {
            "actors": {"A": actor_a, "B": actor_b, "C": actor_c},
            "risk_tolerance": risk_tolerance,
            "max_turns": 5,
            "strategies": {},
            "model_mode": model_mode
        }
        
        # Start Worker
        q = queue.Queue()
        st.session_state["queue"] = q
        request_text = f"Analyze stability given: {p_data['ctx']}"
        
        worker = Worker(q, request_text, context, st.session_state["control"])
        worker.start()
        st.session_state["worker"] = worker
        st.rerun()

    if st.session_state.get("worker"):
        if st.button("🛑 EMERGENCY STOP", type="secondary"):
            st.session_state["control"]["stop"] = True
            st.session_state["worker"] = None
            st.warning("Sequence Aborted.")
            st.rerun()

# --- Main Dashboard ---
st.title("🦅 Strategic Operations Console")

col_left, col_mid, col_right = st.columns([1.5, 2, 1.5])

# LEFT: Timeline & Plan
with col_left:
    st.subheader("📡 Live Feed")
    components.render_timeline(st.session_state["timeline"])
    
    # Show Plan if available
    run_state = st.session_state["run_state"]
    if "plan" in run_state and run_state["plan"]:
        with st.expander("Execution Plan", expanded=True):
            for step in run_state["plan"].get("steps", []):
                st.markdown(f"**[{step.get('agent','SYS').upper()}]** {step.get('objective')}")


# MIDDLE: Decision Desk
with col_mid:
    st.subheader("🎯 Command Decision")
    
    run_state = st.session_state["run_state"]
    
    # Priority: Final Decision > Judgment > Constraint > none
    display_decision = None
    
    if run_state.get("final_report"):
        display_decision = run_state["final_report"].get("final_decision")
        status = run_state["final_report"].get("status")
        
        if status == "DEGRADED_LLM":
            st.warning("⚠️ Partial intelligence — system operating under degraded capacity")
            
    elif run_state.get("judgment_result"):
        # Show intermediate judgment
        pass 
        
    components.render_decision_card(display_decision)
    
    st.divider()
    components.render_specialist_breakdown(run_state.get("specialist_decisions", []))

# RIGHT: Simulation & Audit
with col_right:
    # Thought Stream (New)
    components.render_thought_stream(run_state.get("specialist_decisions", []))
    st.divider()

    st.subheader("🎲 Simulation")
    
    sim_res = run_state.get("simulation_result")
    if sim_res:
        valid = sim_res.get("outcome") != "CRASH"
        st.metric("Model Stability", f"{sim_res.get('stability_score', 0):.2f}")
        st.metric("Turns Simluated", sim_res.get("turn_count", 0))
        
        if not valid:
             st.error(f"Simulation Failed: {sim_res.get('outcome')}")
        else:
             st.success("Simulation Validated")
             
    else:
        st.caption("Awaiting Strategy Approval...")
        
    st.divider()
    components.render_audit_panel(st.session_state["run_state"])

# --- Event Loop ---
if st.session_state.get("worker"):
    try:
        # Drain queue roughly
        while True:
            msg = st.session_state["queue"].get_nowait()
            
            # Timestamp
            ts = datetime.now().isoformat()
            
            if msg["type"] == "status":
                st.session_state["timeline"].insert(0, {
                    "timestamp": ts, 
                    "source": "SYS", 
                    "text": msg["payload"], 
                    "status": "running"
                })
                
            elif msg["type"] == "plan":
                st.session_state["run_state"]["plan"] = msg["payload"]
                st.session_state["timeline"].insert(0, {
                    "timestamp": ts, 
                    "source": "PLANNER", 
                    "text": "Execution Plan Optimized", 
                    "status": "success"
                })
                
            elif msg["type"] == "specialist_decision":
                # Aggregate into list
                if "specialist_decisions" not in st.session_state["run_state"]:
                    st.session_state["run_state"]["specialist_decisions"] = []
                st.session_state["run_state"]["specialist_decisions"].append(msg["payload"])
                
                agent = msg.get("agent", "AGENT")
                st.session_state["timeline"].insert(0, {
                    "timestamp": ts, 
                    "source": agent.upper(), 
                    "text": "Intelligence Received", 
                    "status": "success"
                })
                
            elif msg["type"] == "composite":
                st.session_state["run_state"]["composite_decision"] = msg["payload"]
                
            elif msg["type"] == "constraint":
                res = msg["payload"]
                safe = res.get("is_safe")
                st.session_state["timeline"].insert(0, {
                    "timestamp": ts, 
                    "source": "CONSTRAINT", 
                    "text": "Safety Check Passed" if safe else f"Safety Blocked: {res.get('warnings')}", 
                    "status": "success" if safe else "error"
                })
                
            elif msg["type"] == "judgment":
                 # Typically judgment is final approval
                 res = msg["payload"]
                 approved = res.get("is_approved")
                 st.session_state["run_state"]["judgment_result"] = res
                 st.session_state["timeline"].insert(0, {
                    "timestamp": ts, 
                    "source": "JUDGMENT", 
                    "text": "Strategy Approved" if approved else "Strategy Rejected (Looping)", 
                    "status": "success" if approved else "warning"
                })

            elif msg["type"] == "simulation":
                st.session_state["run_state"]["simulation_result"] = msg["payload"]
                st.session_state["timeline"].insert(0, {
                    "timestamp": ts, 
                    "source": "SIMULATION", 
                    "text": "Wargame Complete", 
                    "status": "success"
                })
                
            elif msg["type"] == "done":
                st.session_state["run_state"]["final_report"] = msg["payload"]
                st.session_state["timeline"].insert(0, {
                    "timestamp": ts, 
                    "source": "SYS", 
                    "text": "Mission Complete", 
                    "status": "success"
                })
                st.session_state["worker"] = None # Stop polling
                
            elif msg["type"] == "error":
                st.error(msg["payload"])
                st.session_state["worker"] = None
                
    except queue.Empty:
        pass
        
    time.sleep(0.5)
    st.rerun()
