from typing import Any, Dict
from core.schemas import Decision, DecisionType
from agents.base_agent import BaseAgent

class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__("security")

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        instruction = inputs.get("instruction")
        context = inputs.get("context", {})
        
        prompt = f"""
        {SECURITY_SYSTEM_PROMPT}
        
        ---
        SCENARIO CONTEXT: {context}
        SPECIFIC INSTRUCTION: {instruction}
        """
        
        return await self.llm_client.generate_structured_output(
            prompt,
            response_schema=SecurityAssessment.model_json_schema(),
            model="llama-3.1-8b-instant"
        )

SECURITY_SYSTEM_PROMPT = """You are SECURITY_ANALYSIS_AGENT.

ROLE
- Analyze strategic risks, deterrence, and stability.
- Output a typed DECISION object.

OUTPUT SCHEMA
- decision_type: APPROVE (Safe/Beneficial), REJECT (Dangerous), MODIFY (Needs changes), ABORT (Critical Failure).
- recommended_action: Short action phrase.
- risk_score: 0 (Safe) to 10 (Critical).
- rationale_summary: Max 3 bullet points.

PRINCIPLES
- If risk > 7, REJECT or ABORT.
- Focus on survival and stability.
"""
