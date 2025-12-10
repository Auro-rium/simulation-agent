from orchestration.manager import run_sync_wrapper
import logging

logger = logging.getLogger("adk_app")

class MultiAgentApp:
    def __init__(self):
        pass # No explicit INIT needed for new manager as it is stateless/global instance usage

    def handle_request(self, user_request: str, context: dict = None) -> dict:
        if context is None:
            context = {}
        logger.info(f"Received request: {user_request}")
        # Call the v0.2.0 Async Manager via sync wrapper
        final_report_dict = run_sync_wrapper(user_request, context)
        
        # TRANSFORMATION LAYER:
        # The UI expects the old schema for "plan_summary", "specialist_findings", "simulation_result"
        # The new report has objects. We need to map them back for UI compatibility until UI is updated.
        
        # 1. Map Plan
        plan_obj = final_report_dict.get("plan", {})
        plan_steps = [s.get("task") for s in plan_obj.get("steps", [])]
        
        # 2. Map Specialists
        spec_outputs = final_report_dict.get("specialist_outputs", [])
        findings = {}
        for so in spec_outputs:
            agent_key = so.get("agent", "").lower()
            # Try to get nested analysis string or json dump
            val = so.get("output", {})
            if isinstance(val, dict):
                 val = val.get("analysis", str(val))
            findings[agent_key] = str(val)
            
        # 3. Map Simulation
        sim_res = final_report_dict.get("simulation_result", {})
        sim_history = []
        for h in sim_res.get("simulation_history", []):
            sim_history.append({
                "turn": h.get("turn"),
                "actor": h.get("actor"),
                "action": h.get("action"),
                "result": h.get("result")
            })
            
        constraints = final_report_dict.get("constraint_result", {})
            
        return {
            "original_request": final_report_dict.get("request"),
            "plan_summary": plan_steps,
            "specialist_findings": findings,
            "constraints": constraints,
            "simulation_result": {"simulation_history": sim_history, "outcomes": sim_res.get("outcomes")},
            "manager_report": final_report_dict.get("manager_report")
        }

# Global instance
app_instance = MultiAgentApp()

def entry_point(request_body: dict):
    """
    Standard entry point for generic runners.
    Expects {'request': '...', 'context': {...}}
    """
    req = request_body.get("request")
    ctx = request_body.get("context", {})
    return app_instance.handle_request(req, ctx)
