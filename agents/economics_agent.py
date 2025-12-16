from typing import Any, Dict
from core.schemas import Decision, DecisionType
from agents.base_agent import BaseAgent

class EconomicsAgent(BaseAgent):
    def __init__(self):
        super().__init__("economics")

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        instruction = inputs.get("instruction")
        context = inputs.get("context", {})
        
        prompt = f"""
        {ECONOMICS_SYSTEM_PROMPT}

        ---
        SCENARIO CONTEXT: {context}
        SPECIFIC INSTRUCTION: {instruction}
        """
        
        return await self.llm_client.generate_structured_output(
            prompt,
            response_schema=EconAssessment.model_json_schema(),
            model="llama-3.1-8b-instant"
        )

ECONOMICS_SYSTEM_PROMPT = """You are ECONOMICS_SPECIALIST_AGENT.

ROLE
- Analyze costs, benefits, and incentives.
- Output a typed DECISION object.

OUTPUT SCHEMA
- decision_type: APPROVE (Profitable/Sustainable), REJECT (Too Costly), MODIFY (Cheaper Option), ABORT (Bankrupts State).
- recommended_action: Economic policy.
- risk_score: 0-10 (Financial Risk).
- rationale_summary: Max 3 bullet points.

PRINCIPLES
- No free lunch.
- High cost = High risk score.
"""
