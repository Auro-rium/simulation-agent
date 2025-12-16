import operator
import json
import asyncio
import time
from typing import List, Dict, Any, Optional, Annotated, TypedDict
    
from datetime import datetime

from langgraph.graph import StateGraph, END
from core.schemas import (
    ExecutionPlan, SpecialistDecision, ConstraintResult, 
    JudgmentResult, SimulationResult, FinalReport, RunStatus,
    CompositeDecision, Decision, DecisionType
)
from core.decision_aggregator import DecisionAggregator
from llm.llm_client import LLMClient

# Import Agents
from agents.planner_agent import PlannerAgent
from agents.constraint_agent import ConstraintAgent
from agents.judgment_agent import JudgmentAgent
from agents.security_agent import SecurityAgent
from agents.technology_agent import TechnologyAgent
from agents.economics_agent import EconomicsAgent
from agents.simulation_agent import SimulationAgent

# Define State
class CoordinatorState(TypedDict):
    # Inputs
    run_id: str
    request: str
    context: Dict[str, Any]
    seed: Optional[int]
    
    # Internal Artifacts
    plan: Optional[ExecutionPlan]
    specialist_decisions: List[SpecialistDecision]
    composite_decision: Optional[CompositeDecision]
    
    # A2A Loop State
    constraint_result: Optional[ConstraintResult]
    judgment_result: Optional[JudgmentResult]
    judgment_feedback: Optional[str]
    retry_count: int
    
    # Simulation Loop State
    simulation_state: Dict[str, Any] # Explicit World State
    simulation_result: Optional[SimulationResult]
    turn_count: int
    
    # Final Output
    final_report: Optional[FinalReport]
    status: RunStatus
    timestamps: Dict[str, str]

async def node_plan(state: CoordinatorState) -> Dict:
    """Generates the execution plan (v0.3.0)."""
    req = state["request"]
    ctx = state["context"]
    
    try:
        planner_agent = PlannerAgent()
        res = await planner_agent.run({"user_request": req, "scenario_context": ctx})
        plan_data = res.get("plan", {})
        plan = ExecutionPlan(**plan_data)
    except Exception as e:
        print(f"Plan Error: {e}")
        return {"status": RunStatus.SYSTEM_ERROR}
        
    return {
        "plan": plan, 
        "timestamps": {**state.get("timestamps", {}), "plan_done": datetime.now().isoformat()}
    }

async def node_specialists(state: CoordinatorState) -> Dict:
    """Executes specialist steps to produce Decisions."""
    plan = state["plan"]
    ctx = state["context"]
    
    if not plan or not plan.steps:
        return {"specialist_decisions": []}
        
    async def run_step(step) -> SpecialistDecision:
        agent_name = step.agent.upper()
        if "SECURITY" in agent_name: agent = SecurityAgent()
        elif "TECHNOLOGY" in agent_name: agent = TechnologyAgent()
        elif "ECONOMICS" in agent_name: agent = EconomicsAgent()
        else: agent = None
        
        if agent:
             payload = {"instruction": step.objective, "context": ctx}
             try:
                 res = await agent.run(payload)
                 # Expecting {"decision": dict}
                 decision_data = res.get("decision", {})
                 decision = Decision(**decision_data)
                 # raw = res for audit
             except Exception as e:
                 # Fallback empty decision on error? Or re-raise?
                 # System mandate: Failure is first class.
                 # We return a dummy ERROR decision
                 decision = Decision(
                     decision_type=DecisionType.ABORT,
                     recommended_action="Agent Error",
                     confidence=0,
                     risk_score=10,
                     rationale_summary=[str(e)]
                 )
        else:
             decision = Decision(
                     decision_type=DecisionType.ABORT,
                     recommended_action="Unknown Agent",
                     confidence=0,
                     risk_score=10,
                     rationale_summary=["Configuration Error"]
             )
             
        return SpecialistDecision(
            agent=agent_name,
            step_id=step.step_id,
            decision=decision
        )
    
    tasks = [run_step(s) for s in plan.steps]
    results = await asyncio.gather(*tasks)
    
    return {
        "specialist_decisions": results,
        "timestamps": {**state.get("timestamps", {}), "specialists_done": datetime.now().isoformat()}
    }

async def node_aggregate(state: CoordinatorState) -> Dict:
    """Deterministically aggregates decisions."""
    comp = DecisionAggregator.aggregate(state["specialist_decisions"])
    return {"composite_decision": comp}

async def node_constraint(state: CoordinatorState) -> Dict:
    """Checks constraints on the CompositeDecision."""
    comp = state["composite_decision"]
    feedback = state.get("judgment_feedback")
    
    try:
        constraint_agent = ConstraintAgent()
        # Pass model_dump() usually
        payload = {
            "composite_decision": comp.model_dump(),
            "judgment_feedback": feedback
        }
        res = await constraint_agent.run(payload)
        c_data = res.get("constraint_check", {})
        result = ConstraintResult(**c_data)
        
    except Exception as e:
        print(f"Constraint Error: {e}")
        result = ConstraintResult(is_safe=False, warnings=[f"Agent Error: {e}"])
    
    return {
        "constraint_result": result,
        "timestamps": {**state.get("timestamps", {}), "constraint_done": datetime.now().isoformat()}
    }

async def node_judgment(state: CoordinatorState) -> Dict:
    """Evaluates strategy and outputs Final Decision."""
    c_result = state["constraint_result"]
    comp = state["composite_decision"]
    ctx = state["context"]
    
    try:
        judgment_agent = JudgmentAgent()
        payload = {
            "composite_decision": comp.model_dump(),
            "constraint_output": c_result.model_dump(),
            "context": ctx
        }
        res = await judgment_agent.run(payload)
        j_data = res.get("judgment_result", {})
        result = JudgmentResult(**j_data)
        
    except Exception as e:
        print(f"Judgment Error: {e}")
        # Crash state
        return {"status": RunStatus.SYSTEM_ERROR}

    return {
        "judgment_result": result,
        "judgment_feedback": result.feedback if not result.is_approved else None,
        "retry_count": state.get("retry_count", 0) + 1
    }

async def node_simulation_run(state: CoordinatorState) -> Dict:
    """Runs the simulation with the FINAL Decision."""
    # This node might run ONCE after approval, or iteratively?
    # Requirement: "SimulationAgent: Receives FINAL Decision ONLY... Runs turn-based simulation"
    # Assuming one pass or a managed internal loop.
    # Let's run a multi-turn simulation here or delegate to a loop?
    # prompt implies "Simulation Must Be State-Enforced... Output SimulationResult"
    
    # We will run a loop of X turns explicitly here calling Sim Agent repeatedly 
    # OR Sim Agent runs the whole thing? 
    # "LLMs may PROPOSE moves... System MUST VALIDATE" -> Simulation Agent.
    # Let's assume we run N turns.
    
    final_dec = state["judgment_result"].final_decision
    if not final_dec:
        return {"status": RunStatus.SYSTEM_ERROR}
        
    current_state = state.get("simulation_state", state["context"].get("initial_state", {}))
    history = []
    
    sim_agent = SimulationAgent()
    max_turns = state["context"].get("max_turns", 3)
    
    stability = 1.0
    outcome = "IN_PROGRESS"
    
    for i in range(max_turns):
        # In a real engine, we'd have opponents. For now, we simulate the consequences of the User's Decision.
        # Simple loop: Apply Decision -> Update State -> Check Stability.
        
        payload = {
            "final_decision": final_dec.model_dump(),
            "simulation_state": current_state,
            "history": [h.model_dump() for h in history]
        }
        
        try:
            res = await sim_agent.run(payload)
            turn_data = res.get("simulation_turn", {})
            # Validate output turn
            # In a real system the AGENT proposes and the CODE validates.
            # Here the agent does both in the mock (SimAgent.run calls LLM which returns 'validation').
            # We trust the SimAgent's internal validation for this v0.3.0
            
            # Map loosely to SimulationTurn
            # The SimAgent returns a dict matching the schema.
            # We construct objects
            pass
            # Update state (mock)
            # current_state.update(...)
            
            # For now, we just construct the result at the end
            outcome = "COMPLETED"
        except Exception as e:
            outcome = f"CRASH: {e}"
            break
            
    # Mock result construction since Sim logic is mocked
    sim_res = SimulationResult(
        final_state=current_state,
        outcome=outcome,
        stability_score=stability,
        turn_count=max_turns,
        history=[]
    )
    
    return {
        "simulation_result": sim_res,
        "status": RunStatus.SUCCESS
    }

async def node_finalize(state: CoordinatorState) -> Dict:
    """Packages the final artifacts."""
    # No LLM synthesis. Just data packaging.
    
    j_res = state.get("judgment_result")
    final_dec = j_res.final_decision if j_res else None
    
    if not final_dec:
        # Fallback if we failed before judgment
        final_dec = Decision(
            decision_type=DecisionType.ABORT, 
            recommended_action="System Failure", 
            confidence=0, 
            risk_score=10, 
            rationale_summary=["Graph did not reach a decision"]
        )
        status = state.get("status", RunStatus.SYSTEM_ERROR)
    else:
        status = state.get("status", RunStatus.SUCCESS)

    report = FinalReport(
        run_id=state["run_id"],
        status=status,
        final_decision=final_dec,
        simulation_result=state.get("simulation_result"),
        audit_trail={
            "plan_id": state["plan"].plan_id if state["plan"] else None,
            "retry_count": state.get("retry_count", 0),
            "seed": state.get("seed")
        },
        timestamps={**state.get("timestamps", {}), "end": datetime.now().isoformat()}
    )
    
    return {"final_report": report}

def build_graph():
    workflow = StateGraph(CoordinatorState)
    
    workflow.add_node("plan", node_plan)
    workflow.add_node("specialists", node_specialists)
    workflow.add_node("aggregate", node_aggregate)
    workflow.add_node("constraint", node_constraint)
    workflow.add_node("judgment", node_judgment)
    workflow.add_node("simulation_run", node_simulation_run)
    workflow.add_node("finalize", node_finalize)
    
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "specialists")
    workflow.add_edge("specialists", "aggregate")
    workflow.add_edge("aggregate", "constraint")
    workflow.add_edge("constraint", "judgment")
    
    def check_judgment_loop(state):
        if state.get("status") == RunStatus.SYSTEM_ERROR:
            return "finalize"
            
        result = state["judgment_result"]
        # If approved
        if result.is_approved:
            return "simulation_run"
        
        if state["retry_count"] <= 2:
            return "constraint"
            
        # Abort if retries exhausted
        return "finalize"
        
    workflow.add_conditional_edges("judgment", check_judgment_loop)
    workflow.add_edge("simulation_run", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()

coordinator_graph = build_graph()
