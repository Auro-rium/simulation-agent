from typing import Any, Dict
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class SecurityAssessment(BaseModel):
    key_risks: list[str]
    opportunities_for_A: list[str]
    likely_responses_of_B_and_C: list[str]
    recommended_security_posture_for_A: list[str]
    security_tradeoffs: list[str]

class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__("security")

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        instruction = inputs.get("instruction")
        context = inputs.get("context", {})
        
        prompt = f"""
        {SECURITY_SYSTEM_PROMPT}
        
        ---
        SCENARIO CONTEXT: {context}
        
        SPECIFIC INSTRUCTION: {instruction}
        """
        
        result = self.llm_client.generate_structured_output(
            prompt,
            response_schema=SecurityAssessment.model_json_schema(),
            model_type="fast" # Use Flash for specialist tasks
        )
        return {"security_analysis": result}

SECURITY_SYSTEM_PROMPT = """You are SECURITY_ANALYSIS_AGENT.

ROLE
- Analyze strategic and security implications for abstract actors A, B, C.
- Focus on risks, deterrence, escalation, alliances, and stability.
- Do NOT reference real countries or real conflicts.

INPUT
- A structured description of the scenario and Actor A's goals.

OUTPUT
Return a JSON object:

{
  "key_risks": ["...", "..."],
  "opportunities_for_A": ["...", "..."],
  "likely_responses_of_B_and_C": ["...", "..."],
  "recommended_security_posture_for_A": ["...", "..."],
  "security_tradeoffs": ["...", "..."]
}

PRINCIPLES
- Use first-principles: capabilities, incentives, information, constraints.
- Avoid detailed real-world geopolitics; keep it abstract and general."""
