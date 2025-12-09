from typing import Any, Dict, List
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class SimScenario(BaseModel):
    name: str
    assumptions: List[str]
    expected_behaviour: Dict[str, str]
    qualitative_payoffs: Dict[str, str]
    stability_assessment: str

class SimOutput(BaseModel):
    scenarios: List[SimScenario]
    comparison_summary: str
    recommended_strategy_for_A: List[str]
    key_risks_and_contingencies: List[str]

class SimulationAgent(BaseAgent):
    def __init__(self):
        super().__init__("simulation")

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs conceptual simulations and comparative scenario analyses.
        """
        actors = inputs.get("actors", {"A": "Abstract A", "B": "Abstract B", "C": "Abstract C"})
        strategies = inputs.get("strategies", {})
        
        prompt = f"""
        {SIMULATION_SYSTEM_PROMPT}
        
        ---
        ACTORS: {actors}
        STRATEGIES / CONSTRAINTS: {strategies}
        """
        
        result = self.llm_client.generate_structured_output(
            prompt,
            response_schema=SimOutput.model_json_schema(),
            model_type="reasoning"
        )
        
        return {
            "simulation_result": result,
            # Synthesize a simple history for UI compatibility if needed, or just let the result stand
            "simulation_history": [s.name + ": " + s.stability_assessment for s in result.scenarios]
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
