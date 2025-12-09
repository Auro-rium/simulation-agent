from typing import Any, Dict
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class TimeHorizons(BaseModel):
    short_term: str
    medium_term: str
    long_term: str

class TechAssessment(BaseModel):
    critical_technologies: list[str]
    feasibility_assessment: str
    time_horizons: TimeHorizons
    tech_advantages_for_A: list[str]
    tech_risks_or_dependencies: list[str]

class TechnologyAgent(BaseAgent):
    def __init__(self):
        super().__init__("technology")

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        instruction = inputs.get("instruction")
        context = inputs.get("context", {})
        
        prompt = f"""
        {TECHNOLOGY_SYSTEM_PROMPT}

        ---
        SCENARIO CONTEXT: {context}
        
        SPECIFIC INSTRUCTION: {instruction}
        """
        
        result = self.llm_client.generate_structured_output(
            prompt,
            response_schema=TechAssessment.model_json_schema(),
            model_type="fast"
        )
        return {"technology_analysis": result}

TECHNOLOGY_SYSTEM_PROMPT = """You are TECHNOLOGY_ANALYSIS_AGENT.

ROLE
- Analyze technological aspects of the scenario for Actor A vs actors B and C.

INPUT
- Scenario description
- Goals for Actor A

OUTPUT
Return:

{
  "critical_technologies": ["...", "..."],
  "feasibility_assessment": "Short narrative",
  "time_horizons": {
    "short_term": "...",
    "medium_term": "...",
    "long_term": "..."
  },
  "tech_advantages_for_A": ["...", "..."],
  "tech_risks_or_dependencies": ["...", "..."]
}

PRINCIPLES
- Anchor assessments in feasibility, speed, cost, and robustness.
- Consider how B and C might catch up or leapfrog."""
