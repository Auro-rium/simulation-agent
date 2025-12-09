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

st.set_page_config(page_title="Agentic Simulation", layout="wide")

st.title("Diplomatic Simulation Agent System")
st.markdown("Use Google ADK + Gemini 2.5 Agents to plan and simulate complex scenarios.")

# Sidebar for configuration
st.sidebar.header("Scenario Settings")
max_turns = st.sidebar.slider("Max Turns", 1, 10, 3)

# Load default config for convenience
try:
    with open("configs/example_scenario.yaml", "r") as f:
        default_config = yaml.safe_load(f)
except:
    default_config = {}

# Dynamic Inputs
col1, col2 = st.columns(2)

with col1:
    st.subheader("Global Context")
    global_condition = st.text_area("Situation Description", 
        value=default_config.get("context", {}).get("global_condition", "Global energy crisis, high inflation"))
    risk_tolerance = st.selectbox("Risk Tolerance", ["Low", "Moderate", "High"], index=1)

with col2:
    st.subheader("Actors")
    # Simple JSON editor for actors to allow flexibility
    actors_json = st.text_area("Actors (JSON)", 
        value=json.dumps(default_config.get("actors", {"A": "...", "B": "..."}), indent=2),
        height=150)
    
    strategies_json = st.text_area("Strategies (JSON)", 
        value=json.dumps(default_config.get("strategies", {}), indent=2),
        height=150)

user_request = st.text_input("Analysis Request", 
    value="Analyze a potential trade agreement negotiation between these actors.")

if st.button("Run Simulation", type="primary"):
    with st.spinner("Agents are thinking... (Planning → Specialists → Simulation)"):
        try:
            # Reconstruct context
            try:
                actors = json.loads(actors_json)
                strategies = json.loads(strategies_json)
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON in Actors/Strategies: {e}")
                st.stop()

            context = {
                "max_turns": max_turns,
                "global_condition": global_condition,
                "risk_tolerance": risk_tolerance,
                "actors": actors,
                "strategies": strategies
            }

            # Execute via ADK App (Direct call)
            result = app_instance.handle_request(user_request, context)
            
            # --- Display Results ---
            st.success("Simulation Complete!")

            if "manager_report" in result:
                st.markdown("### 📋 Final Manager Report")
                st.info(result["manager_report"])
            
            # Plan
            st.markdown("### 1. Strategic Plan")
            with st.expander("View Plan Details", expanded=True):
                st.write(result.get("plan_summary", []))
            
            # Specialists
            st.markdown("### 2. Specialist Assessments")
            tabs = st.tabs(["Security", "Technology", "Economics"])
            findings = result.get("specialist_findings", {})
            
            with tabs[0]:
                st.json(findings.get("security", {}))
            with tabs[1]:
                st.json(findings.get("technology", {}))
            with tabs[2]:
                st.json(findings.get("economics", {}))

            # Constraints
            st.markdown("### 3. Constraint Check")
            st.info(f"Authorized: {result.get('constraints', {}).get('is_safe')}")
            if result.get('constraints', {}).get('warnings'):
                st.warning(result['constraints']['warnings'])
            
            # Simulation
            st.markdown("### 4. Game-Theoretic Simulation")
            sim_res = result.get("simulation_result")
            sim_hist = sim_res.get("simulation_history", []) if isinstance(sim_res, dict) else result.get("simulation_result", {}).get("simulation_history", [])
            
            # Handle slight schema variations depending on agent output structure
            if "simulation_history" in result.get("simulation_result", {}):
                 sim_hist = result["simulation_result"]["simulation_history"]
            
            if isinstance(sim_hist, list):
                for move in sim_hist:
                    st.text(move)
            else:
                st.write(sim_hist)

            st.markdown("#### Final Outcome")
            st.write(result.get("simulation_result", {}).get("simulation_result", "No final result"))
            
            # Debug Raw
            with st.expander("Raw Output JSON"):
                st.json(result)

        except Exception as e:
            st.error(f"Execution failed: {str(e)}")
            import traceback
            st.text(traceback.format_exc())
