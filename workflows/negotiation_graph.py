from typing import TypedDict, List, Dict, Any, Annotated
import operator
from langgraph.graph import StateGraph, END
from llm.llm_client import LLMClient

# Define the state of the simulation
class SimulationState(TypedDict):
    actors: Dict[str, Any]      # Actor definitions (A, B, C)
    history: List[str]          # Log of events/moves
    turn_count: int             # Current turn number
    max_turns: int              # Max turns to simulate
    current_actor: str          # Who's turn is it?
    strategies: Dict[str, str]  # Current strategy for each actor
    final_result: str           # Final outcome summary

# Instantiate LLM Client (this will be used by nodes)
llm_client = LLMClient()

def node_plan_move(state: SimulationState) -> Dict[str, Any]:
    """Actor plans their next move based on history and strategy."""
    actor_id = state["current_actor"]
    actor_data = state["actors"].get(actor_id, {})
    history_str = "\n".join(state["history"][-5:]) # Last 5 moves context
    
    prompt = f"""
    You are simulating Actor {actor_id} in a strategic scenario.
    Your Profile: {actor_data}
    Current Strategy: {state['strategies'].get(actor_id, 'Adapt and survive')}
    
    Recent History:
    {history_str}
    
    Decide your next move. It should be abstract but strategic (e.g., "Signal cooperation," "Fortify position").
    Keep it brief (1 sentence).
    """
    
    # Using Pro for reasoning about the move
    move = llm_client.generate_text(prompt, model_type="reasoning")
    
    new_history_entry = f"Turn {state['turn_count']}: Actor {actor_id} performed: {move.strip()}"
    
    return {
        "history": [new_history_entry], # Append to history (LangGraph handles append if annotated correctly, but for simple TypedDict we just return the update key)
        # Note: In TypedDict with operator.add default behavior in latest LangGraph for list is strictly replace unless we use Annotated[List, operator.add]. 
        # For this demo, we'll manually handle list extension in the reducer or assume we just return the diff.
        # Let's fix the State definition to be robust. For now, we will return the FULL list or rely on the caller to merge.
        # Actually LangGraph's StateGraph with TypedDict usually replaces keys. 
        # To make it safer without complex reducers in this file, we will read, append, and return the full list.
    }

def node_update_state(state: SimulationState) -> Dict[str, Any]:
    """Updates the turn and actor pointer."""
    actors = list(state["actors"].keys())
    current_idx = actors.index(state["current_actor"])
    next_idx = (current_idx + 1) % len(actors)
    next_actor = actors[next_idx]
    
    next_turn = state["turn_count"]
    if next_idx == 0:
        next_turn += 1
        
    return {
        "current_actor": next_actor,
        "turn_count": next_turn
    }

def node_evaluate_outcome(state: SimulationState) -> Dict[str, Any]:
    """Summarizes the final state."""
    prompt = f"""
    Analyze the following simulation history and determine the outcome.
    
    Actors: {state['actors']}
    History:
    {state['history']}
    
    Provide a strategic summary of who 'won' or if equilibrium was reached.
    """
    result = llm_client.generate_text(prompt, model_type="reasoning")
    return {"final_result": result}

# --- Graph Construction ---

def create_negotiation_graph():
    # We need a custom reducer for history to append instead of overwrite if we were being pure, 
    # but for simplicity in this demo, the nodes will read-copy-update the list or we rely on standard behavior.
    # To be safe with standard TypedDict, nodes should return the modified key.
    # Here, we will make 'node_plan_move' append to the existing list in memory and return it.
    
    # Redefine node slightly to be safe with standard replacement semantics
    def safe_plan_move(state):
        h = list(state["history"]) # copy
        # Reuse logic
        actor_id = state["current_actor"]
        actor_data = state["actors"].get(actor_id, {})
        history_str = "\n".join(h[-5:])
        prompt = f"Roleplay {actor_id}. Profile: {actor_data}. History: {history_str}. One sentence move:"
        move = llm_client.generate_text(prompt, model_type="fast", temperature=0.5)
        h.append(f"Round {state['turn_count']} - {actor_id}: {move.strip()}")
        return {"history": h}

    workflow = StateGraph(SimulationState)
    
    workflow.add_node("plan_move", safe_plan_move)
    workflow.add_node("update_turn", node_update_state)
    workflow.add_node("evaluate", node_evaluate_outcome)
    
    workflow.set_entry_point("plan_move")
    
    def check_end(state):
        if state["turn_count"] > state["max_turns"]:
            return "evaluate"
        return "update_turn"
    
    workflow.add_edge("update_turn", "plan_move") # Loop back
    
    workflow.add_conditional_edges(
        "plan_move",
        check_end,
        {
            "evaluate": "evaluate",
            "update_turn": "update_turn" # Actually prompt -> update -> check -> prompt is better loop
        }
    )
    
    # Correction: The flow should be Plan -> Update -> Check.
    # Let's rewire: Plan -> Check -> (Update -> Plan) OR (Evaluate)
    # Actually, let's keep it simple: Plan -> Update -> Conditional(End or Plan)
    
    workflow = StateGraph(SimulationState)
    workflow.add_node("agent_move", safe_plan_move)
    workflow.add_node("next_turn", node_update_state)
    workflow.add_node("finalize", node_evaluate_outcome)
    
    workflow.set_entry_point("agent_move")
    workflow.add_edge("agent_move", "next_turn")
    
    def should_continue(state):
        if state["turn_count"] >= state["max_turns"]:
            return "finalize"
        return "agent_move"
        
    workflow.add_conditional_edges("next_turn", should_continue)
    workflow.add_edge("finalize", END)
    
    return workflow.compile()
