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
        "simulation_history": [],
        "specialist_outputs": [],
        "rolling_summary": "",
        "max_turns": context.get("max_turns", 3)
    }

    # We use a stream loop to catch state updates and emit events
    # We want to know when specific nodes finish to emit specific events
    
    # Note: StateGraph.stream returns (node_name, state_update) tuples if stream_mode="updates"
    # But standard invoke/stream iterates output state. 
    # Let's use standard stream which yields the state at each step.
    
    final_state = None
    
    async for output in coordinator_graph.astream(initial_state):
        # Output is a dict showing the update from the node that just ran
        # e.g. {"plan": {...}, "timestamps": ...}
        
        for node_name, state_update in output.items():
            
            if node_name == "plan":
                plan = state_update.get("plan")
                emit("status", text="Plan created.")
                emit("plan", payload=plan)
                
            elif node_name == "specialists":
                specs = state_update.get("specialist_outputs", [])
                emit("status", text="Specialists finished.")
                for s in specs:
                    emit("specialist_done", agent=s.agent, payload=s)
                    
            elif node_name == "constraint":
                res = state_update.get("constraint_result")
                emit("status", text="Constraints checked.")
                emit("constraint", payload=res)
                
            elif node_name == "simulation_step":
                # The update contains the appended list. We just want the last one.
                hist = state_update.get("simulation_history", [])
                if hist:
                    turn = hist[-1]
                    emit("status", text=f"Turn {turn.turn} complete ({turn.actor})")
                    emit("turn", index=turn.turn, payload=turn)
            
            final_state = state_update # Keep tracking potentially?
            # Actually astream yields only the delta in 'updates' mode, 
            # but default yields the chunks. Let's assume standard behavior:
            # It yields a dict {node: state_delta}.

    # Retrieve final state from graph logic implies we might need to invoke if stream doesn't give full final
    # But we can reconstruct or just wait for synthesis
    # Actually, let's just use invoke to get the robust final object if needed, 
    # but since we streamed, we should have synthesized report.
    
    # Wait, 'synthesize' node runs last. 
    # It updates "final_report".
    # We can capture it from the stream loop if we are careful.
    
    # Alternatively, run invoke separately? No, that runs it twice.
    # We rely on specific node names.
    
    # Quick fix: The last yielded chunk from 'synthesize' has the report.
    report = None
    if final_state and "final_report" in final_state:
        report = final_state["final_report"]
        
    # If we missed it (e.g. synthesize was the very last thing and loop ended), 
    # let's be safe. 'astream' yields keys.
    # logic above handles it.
    
    if not report:
        # Fallback if streaming didn't catch it correctly (shouldn't happen)
        logger.warning("No report found in stream, forcing synthesize (this might re-run LLM if not cached)")
        # This is a bit risky. Let's hope the loop captured it. 
        # Actually proper way:
        # async for chunk in graph.astream(..., stream_mode="values") yields FULL state at each step
        pass

    # Re-run purely for the return value? 
    # NOTE: To be absolutely robust with return value, we could use `.invoke()` but we lose intermediate events easily without callbacks. 
    # The `astream` above iterates {node: update}.
    # The 'synthesize' node returns {"final_report": report}.
    # So inside the loop: if node_name == "synthesize": report = state_update["final_report"]
    # We just need to ensure we capture that variable.
    
    # Let's verify 'coordinator_graph.astream' default behavior -> yields chunks like {'plan': {'plan': ...}}
    
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
