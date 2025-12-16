"""
Core orchestration logic using LangGraph.
"""
import asyncio
import json
import uuid
import logging
import os
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from orchestration.graph import coordinator_graph, CoordinatorState
from core.schemas import FinalReport

# Initialize Logger
logger = logging.getLogger("manager_run")

async def manager_run(
    user_request: str, 
    context: Dict[str, Any], 
    *, 
    seed: Optional[int] = None, 
    stream: bool = False, 
    progress_callback: Optional[Callable[[Dict], None]] = None
) -> Dict[str, Any]:
    """
    Main entry point for running a simulation task via LangGraph.
    """
    run_id = str(uuid.uuid4())
    start_ts = datetime.now()
    
    # Helper for events
    def emit(type_: str, payload: Any = None, **kwargs):
        if progress_callback:
            event = {"type": type_, "timestamp": datetime.now().isoformat(), **kwargs}
            if payload:
                # Helper to dump pydantic
                if hasattr(payload, "model_dump"):
                    event["payload"] = payload.model_dump()
                else:
                    event["payload"] = payload
            try:
                if asyncio.iscoroutinefunction(progress_callback):
                    pass 
                else:
                    progress_callback(event)
            except Exception as e:
                logger.warning(f"Callback error: {e}")

    emit("status", text="Initializing Graph...")
    
    initial_state: CoordinatorState = {
        "request": user_request,
        "context": context,
        "seed": seed,
        "run_id": run_id,
        "timestamps": {"start": start_ts.isoformat()},
        "turn_count": 0,
        "specialist_decisions": [],
        "simulation_state": context.get("initial_state", {}),
        "status": "RUNNING", # Temporary, will be typed enum in graph
        "retry_count": 0,
        "judgment_feedback": None,
        "plan": None,
        "composite_decision": None,
        "constraint_result": None,
        "judgment_result": None,
        "simulation_result": None,
        "final_report": None
    }

    report = None

    async for output in coordinator_graph.astream(initial_state):
        for node_name, state_update in output.items():
            
            if node_name == "plan":
                plan = state_update.get("plan")
                emit("status", text="Execution Plan created.")
                emit("plan", payload=plan)
                
            elif node_name == "specialists":
                specs = state_update.get("specialist_decisions", [])
                emit("status", text="Specialists decisions received.")
                for s in specs:
                    emit("specialist_decision", agent=s.agent, payload=s)

            elif node_name == "aggregate":
                comp = state_update.get("composite_decision")
                emit("status", text="Decisions Aggregated.")
                emit("composite", payload=comp)
                    
            elif node_name == "constraint":
                res = state_update.get("constraint_result")
                emit("status", text="Safety Constraints Checked.")
                emit("constraint", payload=res)
                
            elif node_name == "judgment":
                 res = state_update.get("judgment_result")
                 status_text = "Judgment: APPROVED" if res.is_approved else "Judgment: REJECTED (Looping)"
                 emit("status", text=status_text)
                 emit("judgment", payload=res)
                 
            elif node_name == "simulation_run":
                res = state_update.get("simulation_result")
                emit("status", text="Simulation Complete.")
                emit("simulation", payload=res)
                
            elif node_name == "finalize":
                if "final_report" in state_update:
                     report = state_update["final_report"]
    
    # Saving to file
    if report:
        # Persistence
        os.makedirs("runs", exist_ok=True)
        report_path = f"runs/{run_id}.json"
        tmp_path = report_path + ".tmp"
        with open(tmp_path, "w") as f:
            f.write(report.model_dump_json(indent=2))
        os.replace(tmp_path, report_path)
        
        emit("done", payload=report)
        return report.model_dump()
        
    return {"error": "Graph execution failed to produce report"}
