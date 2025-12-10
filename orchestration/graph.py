import operator
import json
import asyncio
import time
from typing import List, Dict, Any, Optional, Annotated, TypedDict
    
from datetime import datetime

from langgraph.graph import StateGraph, END
from core.schemas import (
    Plan, Step, SpecialistOutput, ConstraintResult, 
    SimulationResult, FinalReport, SimulationTurn
)
from core.summarizer import update_summary, format_turn
from llm.llm_client import LLMClient

# Define State
class CoordinatorState(TypedDict):
    # Inputs
    run_id: str
    request: str
    context: Dict[str, Any]
    seed: Optional[int]
    
    # Internal Artifacts
    plan: Optional[Plan]
    # We use replace semantics for list here usually, but if we wanted to stream partials 
    # we might use add. For simplicity in this structure, we'll just overwrite or append manually in nodes.
    # However, for specialist outputs, gathering them in one node is easier.
    specialist_outputs: List[SpecialistOutput]
    constraint_result: Optional[ConstraintResult]
    
    # Simulation Loop State
    simulation_history: Annotated[List[SimulationTurn], operator.add]
    rolling_summary: str
    turn_count: int
    actors: Dict[str, str] # ID -> Name
    
    # Final Output
    final_report: Optional[FinalReport]
    timestamps: Dict[str, str]

llm_client = LLMClient()

# Initialize Agents
# We instantiate them globally or per node. Global is better for caching if valid.
from agents.planner_agent import PlannerAgent
from agents.constraint_agent import ConstraintAgent
# Specialists
from agents.security_agent import SecurityAgent
from agents.technology_agent import TechnologyAgent
from agents.economics_agent import EconomicsAgent
from agents.simulation_agent import SimulationAgent

planner_agent = PlannerAgent()
constraint_agent = ConstraintAgent()
specialists = {
    "SECURITY": SecurityAgent(),
    "TECHNOLOGY": TechnologyAgent(),
    "ECONOMICS": EconomicsAgent()
}

async def node_plan(state: CoordinatorState) -> Dict:
    """Generates the execution plan using PlannerAgent."""
    req = state["request"]
    ctx = state["context"]
    
    # Run sync agent in thread
    try:
        res = await asyncio.to_thread(planner_agent.run, {"user_request": req, "scenario_context": ctx})
        # Adapt output: PlannerAgent returns {"plan": dict}
        plan_data = res.get("plan", {})
        plan = Plan(**plan_data)
    except Exception as e:
        print(f"Plan Error: {e}")
        plan = Plan(steps=[])
        
    return {
        "plan": plan, 
        "timestamps": {**state.get("timestamps", {}), "plan_done": datetime.now().isoformat()}
    }

async def node_specialists(state: CoordinatorState) -> Dict:
    """Executes specialist steps in parallel using Agent classes."""
    plan = state["plan"]
    ctx = state["context"]
    
    if not plan or not plan.steps:
        return {"specialist_outputs": []}
        
    async def run_step(step: Step) -> SpecialistOutput:
        agent_name = step.assigned_agent.upper()
        
        # Select Agent
        # Handle some mapping if names don't match exactly
        if "SECURITY" in agent_name: agent = specialists["SECURITY"]
        elif "TECHNOLOGY" in agent_name: agent = specialists["TECHNOLOGY"]
        elif "ECONOMICS" in agent_name: agent = specialists["ECONOMICS"]
        else: agent = None
        
        start = time.time()
        
        if agent:
             # Agent run input
             payload = {"instruction": step.task, "context": ctx}
             try:
                 # Sync call
                 res = await asyncio.to_thread(agent.run, payload)
                 # Specialized extraction based on agent type?
                 # Security -> "security_analysis", etc.
                 # Let's just find the first key or 'analysis'
                 # We can just dump the whole result dict as output
                 output_data = res
             except Exception as e:
                 output_data = {"error": str(e)}
        else:
             output_data = {"error": f"Unknown agent {agent_name}"}
             
        lat = (time.time() - start) * 1000
        
        return SpecialistOutput(
            agent=agent_name,
            step_id=step.step_id,
            output=output_data,
            meta={"latency_ms": lat, "model": "agent-delegated"}
        )
    
    tasks = [run_step(s) for s in plan.steps]
    results = await asyncio.gather(*tasks)
    
    return {
        "specialist_outputs": results,
        "timestamps": {**state.get("timestamps", {}), "specialists_done": datetime.now().isoformat()}
    }

async def node_constraint(state: CoordinatorState) -> Dict:
    """Aggregates and checks constraints using ConstraintAgent."""
    outputs = state["specialist_outputs"]
    ctx = state["context"]
    
    # Prepare input for ConstraintAgent
    # It expects "specialist_outputs" in inputs
    # We should format it nicely or pass raw list?
    # Agent prompt expects string representation usually
    # Let's pass the list of dicts
    
    spec_out_list = [s.model_dump() for s in outputs]
    
    try:
        res = await asyncio.to_thread(constraint_agent.run, {"specialist_outputs": spec_out_list})
        # Returns {"constraint_check": dict}
        c_data = res.get("constraint_check", {})
        # c_data should match ConstraintResult schema now
        
        # Handle possible mismatch if Agent returns different keys due to new prompt vs old prompt
        # But we updated Agent to use ConstraintResult schema
        result = ConstraintResult(**c_data)
    except Exception as e:
        print(f"Constraint Error: {e}")
        result = ConstraintResult(is_safe=False, warnings=[f"Agent Error: {e}"])
    
    # Initialize simulation state if safe
    sim_update = {}
    if result.is_safe:
        actors = ctx.get("actors", {"A": "Actor A", "B": "Actor B"})
        sim_update = {
            "actors": actors,
            "turn_count": 0,
            "simulation_history": [],
            "rolling_summary": ""
        }
        
    return {
        "constraint_result": result,
        "timestamps": {**state.get("timestamps", {}), "constraint_done": datetime.now().isoformat()},
        **sim_update
    }

async def node_simulation_step(state: CoordinatorState) -> Dict:
    """Executes one turn of the simulation."""
    turn = state["turn_count"] + 1
    actors_map = state["actors"]
    actor_ids = list(actors_map.keys())
    current_actor_id = actor_ids[(turn - 1) % len(actor_ids)]
    current_actor_name = actors_map[current_actor_id]
    
    seed = state.get("seed")
    
    prompt = f"""
    Simulation Turn {turn}.
    Actor: {current_actor_name}
    Summary: {state['rolling_summary']}
    Recent: {[format_turn(t.turn, t.actor, t.action) for t in state['simulation_history'][-3:]]}
    Decide move.
    """
    
    res = await llm_client.generate_with_retries(
        prompt, 
        model="gemini-2.5-flash", 
        max_tokens=500,
        seed=seed
    )
    
    turn_obj = SimulationTurn(
        turn=turn,
        actor=current_actor_id,
        action=res["text"].strip(),
        result="success",
        meta=res["meta"]
    )
    
    new_summary = update_summary(state["rolling_summary"], [format_turn(turn, current_actor_id, turn_obj.action)])
    
    return {
        "simulation_history": [turn_obj], # Appends due to Annotated[List, add]
        "rolling_summary": new_summary,
        "turn_count": turn
    }

async def node_synthesize(state: CoordinatorState) -> Dict:
    """Creates final report."""
    req = state["request"]
    plan = state["plan"]
    sim_hist = state.get("simulation_history", [])
    
    sim_res = SimulationResult(
        simulation_history=sim_hist,
        outcomes={"summary": state.get("rolling_summary", "")},
        meta={"turns": state.get("turn_count", 0)}
    )
    
    prompt = f"""
    Final Report for: {req}
    Plan: {plan.model_dump_json() if plan else 'None'}
    Simulation Summary: {state.get('rolling_summary', '')}
    """
    
    res = await llm_client.generate_with_retries(prompt, model="gemini-2.5-pro", seed=state.get("seed"))
    
    report = FinalReport(
        run_id=state.get("run_id", "unknown"),
        request=req,
        plan=plan,
        specialist_outputs=state.get("specialist_outputs", []),
        constraint_result=state.get("constraint_result"),
        simulation_result=sim_res,
        manager_report=res["text"],
        timestamps={**state.get("timestamps", {}), "end": datetime.now().isoformat()},
        metadata={"seed": state.get("seed")}
    )
    
    return {"final_report": report}

def build_graph():
    workflow = StateGraph(CoordinatorState)
    
    workflow.add_node("plan", node_plan)
    workflow.add_node("specialists", node_specialists)
    workflow.add_node("constraint", node_constraint)
    workflow.add_node("simulation_step", node_simulation_step)
    workflow.add_node("synthesize", node_synthesize)
    
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "specialists")
    workflow.add_edge("specialists", "constraint")
    
    def check_safety(state):
        if state["constraint_result"].is_safe:
            max_turns = state["context"].get("max_turns", 3)
            if max_turns > 0:
                return "simulation_step"
        return "synthesize"
        
    workflow.add_conditional_edges("constraint", check_safety)
    
    def check_continue_sim(state):
        max_turns = state["context"].get("max_turns", 3)
        if state["turn_count"] < max_turns:
            return "simulation_step"
        return "synthesize"
        
    workflow.add_conditional_edges("simulation_step", check_continue_sim)
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()

coordinator_graph = build_graph()
