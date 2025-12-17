from typing import Any, Dict, List
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class SimScenario(BaseModel):
    name: str
    assumptions: List[str]
    expected_behaviour: Dict[str, str]
from core.schemas import SimulationResult, SimulationTurn, ValidationResult, Decision

class SimulationAgent(BaseAgent):
    def __init__(self):
        super().__init__("simulation")

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a turn-based simulation enforcing strict state.
        Now receives a FINAL DECISION (Action) to simulate.
        """
        final_decision_dict = inputs.get("final_decision", {})
        current_state = inputs.get("simulation_state", {}) # Current world state
        history = inputs.get("history", [])
        
        # We need the decision object
        try:
             # It might be passed as dict
             decision = Decision(**final_decision_dict)
        except Exception:
             # "Never block on missing intelligence"
             # Construct conservative default
             from core.schemas import DecisionType
             decision = Decision(
                 decision_type=DecisionType.MODIFY,
                 recommended_action="Maintain Status Quo (System Degraded)",
                 confidence=0.1,
                 risk_score=0,
                 rationale_summary=["Input decision invalid; using baseline"]
             )

        prompt = f"""
        {SIMULATION_SYSTEM_PROMPT}
        
        ACTORS: {actors}
        STRATEGIES / CONSTRAINTS: {strategies}
        """
        
        result = self.llm_client.generate_structured_output(
            prompt,
            response_schema=SimulationResult.model_json_schema(),
            model="openai/gpt-oss-120b"
        )
        
        # result is a dict, so we handle it as such
        scenarios = result.get("scenarios", [])
        history = [f"{s.get('name', 'Unknown')}: {s.get('stability_assessment', '')}" for s in scenarios]
        
        return {
            "simulation_result": result,
            "simulation_history": history
        }

SIMULATION_SYSTEM_PROMPT = """You are SIMULATION_AGENT.

ROLE
- Run conceptual simulations and comparative scenario analyses for Actor A vs actors B and C.
- Use first-principles and simple game-theoretic reasoning (e.g., incentives, best responses, equilibria intuition).
- You work over ABSTRACT actors only.

INPUT
- Sanitized, constrained recommendations for Actor A.
- Descriptions of actors A, B, C: objectives, approximate capabilities, and constraints.
- Any candidate strategies or scenarios that the Manager wants compared.

OUTPUT
Return:

{
  "scenarios": [
    {
      "name": "Scenario 1: ...",
      "assumptions": ["...", "..."],
      "expected_behaviour": {
        "A": "...",
        "B": "...",
        "C": "..."
      },
      "qualitative_payoffs": {
        "A": "high/medium/low + explanation",
        "B": "high/medium/low + explanation",
        "C": "high/medium/low + explanation"
      },
      "stability_assessment": "Is this close to a stable outcome? Why or why not?"
    }
  ],
  "comparison_summary": "Which scenario and strategy is best for A, and why.",
  "recommended_strategy_for_A": ["...", "..."],
  "key_risks_and_contingencies": ["...", "..."]
}

PRINCIPLES
- Make incentives explicit.
- Highlight where A’s strategy is robust vs fragile to B/C responses.
- Keep math qualitative unless simple approximate numbers help clarity."""
