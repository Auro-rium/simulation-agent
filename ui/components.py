import streamlit as st
import json
import pandas as pd
from datetime import datetime

def render_risk_gauge(risk_score: int):
    """Renders a visual indicator for risk score (0-10)."""
    # Color mapping
    if risk_score <= 3:
        color = "#00cc00" # Green
        label = "LOW"
    elif risk_score <= 7:
        color = "#ff9900" # Orange
        label = "MEDIUM"
    else:
        color = "#ff3300" # Red
        label = "CRITICAL"
        
    st.markdown(f"""
    <div style="text-align: center; padding: 10px; background-color: #1e1e1e; border-radius: 8px; border: 1px solid #333;">
        <h5 style="margin:0; color: #888;">RISK LEVEL</h5>
        <div style="font-size: 2.5em; font-weight: bold; color: {color};">{risk_score}/10</div>
        <div style="color: {color}; font-weight: bold; letter-spacing: 2px;">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def render_decision_card(decision: dict, title: str = "Final Decision"):
    """Renders the main decision object."""
    if not decision:
        st.info("No decision yet.")
        return

    d_type = decision.get("decision_type", "UNKNOWN")
    action = decision.get("recommended_action", "No action specified.")
    confidence = decision.get("confidence", 0.0)
    risk = decision.get("risk_score", 0)
    rationale = decision.get("rationale_summary", [])
    
    # Type Coloring
    t_color = "#888"
    if d_type == "APPROVE": t_color = "#00cc00"
    elif d_type == "REJECT": t_color = "#ff3300"
    elif d_type == "MODIFY": t_color = "#ff9900"
    elif d_type == "ABORT": t_color = "#ff0000"
    
    with st.container():
        st.markdown(f"### {title}")
        
        # Header Grid
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"""
            <div style="font-size: 1.8em; font-weight: bold; color: {t_color}; border-bottom: 1px solid #333; margin-bottom: 10px;">
                {d_type}
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**Action:** {action}")
            
        with c2:
            render_risk_gauge(risk)
            
        st.divider()
        
        # Confidence Bar
        st.caption(f"CONFIDENCE: {confidence*100:.0f}%")
        st.progress(confidence)
        
        # Rationale
        st.markdown("#### Strategic Rationale")
        for point in rationale:
            st.markdown(f"- {point}")

def render_specialist_breakdown(specialist_decisions: list):
    """Renders collapsible cards for each specialist."""
    st.subheader("Specialist Intelligence")
    
    if not specialist_decisions:
        st.caption("Awaiting intelligence reports...")
        return
        
    for sd in specialist_decisions:
        agent_name = sd.get("agent", "UNKNOWN").upper()
        dec = sd.get("decision")
        fault = sd.get("fault")
        signal = sd.get("signal")

        if fault:
            # Render Fault Card
            border_c = "#ff0000"
            with st.expander(f"[{agent_name}] SYSTEM FAULT (Type: {fault.get('fault_type')})"):
                 st.error(f"Message: {fault.get('message')}")
            continue
            
        if signal:
             # Render Intelligence Signal
             with st.expander(f"[{agent_name}] INTELLIGENCE SIGNAL (Inferred)"):
                 st.info("⚠️ Low-confidence intelligence inferred from partial analysis")
                 st.markdown("**Salvaged Insights:**")
                 for pt in signal.get("summary_points", []):
                     st.markdown(f"- {pt}")
                 st.metric("Inferred Risk Delta", f"{signal.get('inferred_risk_delta'):+d}")
             continue
            
        if not dec:
            # Fallback for missing data
            with st.expander(f"[{agent_name}] NO DATA"):
                st.warning("No decision or fault recorded.")
            continue

        d_type = dec.get("decision_type", "UNKNOWN")
        risk = dec.get("risk_score", 0)
        
        # Color border based on agent type
        border_c = "#444"
        if "SECURITY" in agent_name: border_c = "#d32f2f"
        elif "TECH" in agent_name: border_c = "#0288d1"
        elif "ECON" in agent_name: border_c = "#388e3c"
        
        with st.expander(f"[{agent_name}] {d_type} (Risk: {risk})"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Recommendation:** {dec.get('recommended_action')}")
                st.markdown("**Key Factors:**")
                for r in dec.get("rationale_summary", []):
                    st.markdown(f"- {r}")
            with c2:
                st.metric("Risk", risk)
                st.metric("Conf", f"{dec.get('confidence',0)*100:.0f}%")

def render_thought_stream(specialist_decisions: list):
    """Renders the inner monologue of agents."""
    st.subheader("💭 Agent Thought Stream")
    if not specialist_decisions:
        st.caption("Listening...")
        return
        
    for sd in specialist_decisions:
        trace = sd.get("thought_trace")
        if trace:
            agent = sd.get("agent", "UNKNOWN")
            st.markdown(f"""
            <div style="margin-bottom: 10px; padding: 10px; background-color: #2b2b2b; border-radius: 5px; border-left: 3px solid #666;">
                <strong style="color: #aaa; font-size: 0.8em;">{agent.upper()}</strong><br>
                <em style="color: #ddd;">"{trace}"</em>
            </div>
            """, unsafe_allow_html=True)

def render_timeline(events: list):
    """Renders a vertical timeline of system state."""
    st.subheader("Mission Timeline")
    
    if not events:
        st.caption("System Standby")
        return
        
    for event in events:
        # event = {timestamp, source, text, status}
        ts = event.get("timestamp", "").split("T")[-1][:8] # HH:MM:SS
        source = event.get("source", "SYS")
        text = event.get("text", "")
        status = event.get("status", "info") # info, success, warning, error
        
        # Icon map
        icon = "⚪"
        if status == "success": icon = "🟢"
        elif status == "warning": icon = "🟡"
        elif status == "error": icon = "🔴"
        elif status == "running": icon = "🔵"
        
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 8px; font-family: 'Fira Code', monospace; font-size: 0.9em;">
            <span style="color: #666; margin-right: 10px; min-width: 70px;">{ts}</span>
            <span style="margin-right: 10px;">{icon}</span>
            <strong style="color: #bbb; margin-right: 10px;">[{source}]</strong>
            <span style="color: #e0e0e0;">{text}</span>
        </div>
        """, unsafe_allow_html=True)

def render_audit_panel(state_dump: dict):
    """Debug view of the full JSON state."""
    with st.expander("🕵️ Audit Trail / Raw Data"):
        tabs = st.tabs(["Execution Plan", "Specialists", "Composite", "Simulation", "Full State"])
        
        with tabs[0]:
            st.json(state_dump.get("plan"))
        with tabs[1]:
            st.json(state_dump.get("specialist_decisions"))
        with tabs[2]:
            st.json(state_dump.get("composite_decision"))
        with tabs[3]:
            st.json(state_dump.get("simulation_result"))
        with tabs[4]:
            st.json(state_dump)
