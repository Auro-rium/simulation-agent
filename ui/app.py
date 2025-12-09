import streamlit as st
import sys
import os
import yaml
import json
from dotenv import load_dotenv

# Ensure we can import from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from orchestration.app import app_instance

load_dotenv()

import streamlit as st
import sys
import os
import yaml
import json
from dotenv import load_dotenv

# Ensure we can import from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from orchestration.app import app_instance

load_dotenv()

st.set_page_config(
    page_title="Diplomatic Simulation Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS: WAR ROOM THEME ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
        font-family: 'Roboto', sans-serif;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #f0f6fc !important;
        font-family: 'Helvetica Neue', sans-serif;
        letter-spacing: 1px;
    }
    h1 {
        text-transform: uppercase;
        border-bottom: 2px solid #d29922; /* Gold accent */
        padding-bottom: 10px;
    }
    
    /* Inputs */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: #0d1117;
        color: #c9d1d9;
        border: 1px solid #30363d;
        font-family: 'Fira Code', monospace;
    }
    
    /* JSON Areas */
    .stTextArea textarea {
        font-family: 'Courier New', monospace !important;
        font-size: 0.9em;
    }

    /* Cards / Containers */
    .report-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-left: 4px solid #d29922;
        padding: 20px;
        border-radius: 4px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    .tactical-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 4px;
        height: 100%;
    }
    
    .security-border { border-top: 3px solid #f85149; } /* Red */
    .tech-border { border-top: 3px solid #58a6ff; } /* Blue */
    .econ-border { border-top: 3px solid #3fb950; } /* Green */

    /* Terminal Output */
    .terminal-output {
        background-color: #000000;
        color: #3fb950;
        font-family: 'Courier New', monospace;
        padding: 15px;
        border-radius: 4px;
        border: 1px solid #30363d;
        white-space: pre-wrap;
    }
    
    /* Button */
    .stButton button {
        background-color: #238636;
        color: white;
        border: none;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
        width: 100%;
    }
    .stButton button:hover {
        background-color: #2ea043;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_logo, col_title = st.columns([1, 5])
with col_title:
    st.markdown("# 🏛️ DIPLOMATIC STRATEGIC TERMINAL // CLASSIFIED")
    st.markdown("**AUTHORIZED ACCESS ONLY** | MULTI-AGENT ORCHESTRATION SYSTEM v1.0")

st.divider()

# --- SIDEBAR: MISSION CONTROL ---
st.sidebar.markdown("## 📡 MISSION CONTROL")
st.sidebar.markdown("---")
max_turns = st.sidebar.slider("SIMULATION HORIZON (TURNS)", 1, 10, 3)

st.sidebar.markdown("### 🎲 QUICK LOAD")
if st.sidebar.button("SCENARIO: CHINA vs USA (Trade)"):
    pass # In a real app, this would populate session state
if st.sidebar.button("SCENARIO: CORP MERGER (Tech)"):
    pass

st.sidebar.markdown("---")
st.sidebar.info("SYSTEM STATUS: ONLINE\nAGENTS: READY\nLATENCY: 42ms")


# --- MAIN INPUT AREA: MISSION PARAMETERS ---
st.subheader("📝 MISSION PARAMETERS")

row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.markdown("#### 🌍 GLOBAL INTELLIGENCE")
    global_condition = st.text_area("SITUATION REPORT", 
        value="Global energy crisis, high inflation, rising geopolitical tensions...",
        height=100)
    
    st.markdown("#### ⚖️ POSTURE")
    risk_tolerance = st.selectbox("RISK TOLERANCE (ACTOR A)", ["Low", "Moderate", "High"], index=1)

with row1_col2:
    st.markdown("#### 🎭 ACTOR PROFILES")
    default_actors = {
        "A": "Primary Actor (e.g., Developing Nation)",
        "B": "Competitor/Partner (e.g., Tech Giant)",
        "C": "Observer/Regulator (e.g., International Body)"
    }
    actors_json = st.text_area("ACTOR DEFINITIONS (JSON)", 
        value=json.dumps(default_actors, indent=2),
        height=185)

st.markdown("#### ♟️ STRATEGIC VECTORS")
default_strategies = {
    "Initial_Proposal": "Propose a joint venture with shared IP.",
    "Fallback_Plan": "Seek alternative funding if rejected."
}
strategies_json = st.text_area("CANDIDATE STRATEGIES (JSON)", 
    value=json.dumps(default_strategies, indent=2),
    height=120)

user_request = st.text_input("🎯 OBJECTIVE / REQUEST", 
    value="Analyze the viability of the Initial_Proposal given the context.")

# --- EXECUTION ---
st.markdown("---")
if st.button("🚀 COMMENCE SIMULATION", type="primary"):
    
    # Progress Bar styling
    progress_text = "INITIALIZING AGENT SWARM..."
    my_bar = st.progress(0, text=progress_text)

    try:
        # Reconstruct context
        try:
            actors = json.loads(actors_json)
            strategies = json.loads(strategies_json)
        except json.JSONDecodeError as e:
            st.error(f"❌ DATA CORRUPTION DETECTED: Invalid JSON. {e}")
            st.stop()

        context = {
            "max_turns": max_turns,
            "global_condition": global_condition,
            "risk_tolerance": risk_tolerance,
            "actors": actors,
            "strategies": strategies
        }

        # --- PHASE 1: PLANNING ---
        my_bar.progress(10, text="PHASE 1: STRATEGIC PLANNING...")
        
        # --- PHASE 2: SPECIALISTS ---
        my_bar.progress(30, text="PHASE 2: DEPLOYING SPECIALISTS (SEC/TECH/ECON)...")
        
        # We call the full app, but simulating progress updates would require async callbacks/hooks which is complex in pure streamlit
        # So we just run it.
        result = app_instance.handle_request(user_request, context)
        
        my_bar.progress(80, text="PHASE 4: RUNNING WARGAME SIMULATIONS...")
        my_bar.progress(100, text="PHASE 5: SYNTHESIS COMPLETE.")
        my_bar.empty()
        
        # --- RESULTS AREA: INTELLIGENCE BRIEFING ---
        st.markdown("## 📂 INTELLIGENCE BRIEFING")
        
        # 1. Manager Report (The Big Card)
        if "manager_report" in result:
            st.markdown(f"""
            <div class="report-card">
                <h3>📜 EXECUTIVE SUMMARY</h3>
                <div style="white-space: pre-wrap;">{result['manager_report']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # 2. Tactical Analysis (3-Column Grid)
        st.markdown("### 🔭 TACTICAL ANALYSIS")
        tc1, tc2, tc3 = st.columns(3)
        
        findings = result.get("specialist_findings", {})
        
        with tc1:
            st.markdown('<div class="tactical-card security-border"><h4>🛡️ SECURITY</h4>', unsafe_allow_html=True)
            st.json(findings.get("security", {}), expanded=False)
            st.markdown('</div>', unsafe_allow_html=True)

        with tc2:
            st.markdown('<div class="tactical-card tech-border"><h4>💻 TECHNOLOGY</h4>', unsafe_allow_html=True)
            st.json(findings.get("technology", {}), expanded=False)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with tc3:
            st.markdown('<div class="tactical-card econ-border"><h4>💰 ECONOMICS</h4>', unsafe_allow_html=True)
            st.json(findings.get("economics", {}), expanded=False)
            st.markdown('</div>', unsafe_allow_html=True)
            
        # 3. Constraints & Plan
        st.write("") # Spacer
        with st.expander("🔍 OPERATIONAL PLAN & CONSTRAINTS", expanded=False):
            st.markdown("**STRATEGIC PLAN STEPS:**")
            st.write(result.get("plan_summary", []))
            st.divider()
            st.markdown("**CONSTRAINT CHECK:**")
            c = result.get('constraints', {})
            st.info(f"SAFE: {c.get('is_safe', 'Unknown')}")
            if c.get('warnings'):
                st.warning(f"FLAGS: {c.get('warnings')}")

        # 4. Simulation History (Terminal Style)
        st.markdown("### 🕹️ WARGAME LOGS")
        
        sim_res = result.get("simulation_result")
        
        # Handle schema variations
        sim_hist = []
        if isinstance(sim_res, dict):
            sim_hist = sim_res.get("simulation_history", [])
            # Double check nested
            if "simulation_history" in sim_res: # Sometimes it returns nested
                 sim_hist = sim_res["simulation_history"]
        
        log_text = ""
        if isinstance(sim_hist, list):
            for entry in sim_hist:
                log_text += f"> {entry}\n"
        else:
            log_text = str(sim_hist)
            
        st.markdown(f"""
        <div class="terminal-output">
{log_text}
        </div>
        """, unsafe_allow_html=True)
        
        st.success("✅ MISSION COMPLETE")

    except Exception as e:
        st.error(f"❌ CRITICAL FAILURE: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

