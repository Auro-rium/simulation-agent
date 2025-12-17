from typing import Any, Dict
from core.schemas import Decision, DecisionType, EconAssessment
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
        
        result = await self.llm_client.generate_structured_output(
            prompt,
            response_schema=EconAssessment.model_json_schema(),
            model="openai/gpt-oss-20b",
            max_tokens=200 # Strict cap
        )
        return {"decision": result}

ECONOMICS_SYSTEM_PROMPT = """You are ECONOMICS_SPECIALIST_AGENT.

ROLE
- Analyze costs, benefits, and incentives.
- Output a typed DECISION object.

OUTPUT SCHEMA
- decision_type: APPROVE (Profitable/Sustainable), REJECT (Too Costly), MODIFY (Cheaper Option), ABORT (Bankrupts State).
- recommended_action: Economic policy.
- risk_score: 0-10 (Financial Risk).
- rationale_summary: Max 3 bullet points.


RISK CALIBRATION STANDARD (DO NOT DEVIATE)
0-2: Normal geopolitical friction.
3-4: Elevated tension (diplomatic pressure, sanctions).
5-6: Strategic competition with escalation signals.
7-8: Pre-crisis (military posture, economic warfare).
9-10: Active conflict (kinetic action, blockade).

PRINCIPLES
- No free lunch.
- High cost = High risk score.
- LOWER confidence if uncertain, do NOT inflate risk.
- Schema errors are system faults. Return ONLY valid JSON.
"""
