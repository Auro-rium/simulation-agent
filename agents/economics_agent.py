from typing import Any, Dict
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class Incentives(BaseModel):
    A: str
    B: str
    C: str

class EconAssessment(BaseModel):
    assumptions: list[str]
    costs_for_A: str
    benefits_for_A: str
    distributional_impacts: list[str]
    incentive_analysis: Incentives
    recommended_economic_approach_for_A: list[str]

class EconomicsAgent(BaseAgent):
    def __init__(self):
        super().__init__("economics")

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        instruction = inputs.get("instruction")
        context = inputs.get("context", {})
        
        prompt = f"""
        {ECONOMICS_SYSTEM_PROMPT}

        ---
        SCENARIO CONTEXT: {context}
        
        SPECIFIC INSTRUCTION: {instruction}
        """
        
        result = self.llm_client.generate_structured_output(
            prompt,
            response_schema=EconAssessment.model_json_schema(),
            model_type="fast"
        )
        return {"economics_analysis": result}

ECONOMICS_SYSTEM_PROMPT = """You are ECONOMICS_SPECIALIST_AGENT.

ROLE
- Analyze economic incentives, costs, benefits, and trade-offs for Actor A vs B and C.

INPUT
- Scenario description
- Candidate strategies for Actor A

OUTPUT
Return:

{
  "assumptions": ["...", "..."],
  "costs_for_A": "Qualitative or approximate quantitative summary",
  "benefits_for_A": "Qualitative or approximate quantitative summary",
  "distributional_impacts": ["...", "..."],
  "incentive_analysis": {
    "A": "incentives and constraints",
    "B": "incentives and constraints",
    "C": "incentives and constraints"
  },
  "recommended_economic_approach_for_A": ["...", "..."]
}

PRINCIPLES
- Keep models simple but coherent.
- Make clear when a result depends heavily on a specific assumption."""
