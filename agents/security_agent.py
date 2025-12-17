from typing import Any, Dict
from core.schemas import Decision, DecisionType, SecurityAssessment
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
        
        result = await self.llm_client.generate_structured_output(
            prompt,
            response_schema=SecurityAssessment.model_json_schema(),
            model="openai/gpt-oss-20b",
            max_tokens=200 # Strict cap
        )
        # Ensure result is exactly the dict, Groq sometimes wraps in markdown
        return {"decision": result}

SECURITY_SYSTEM_PROMPT = """You are SECURITY_ANALYSIS_AGENT.

ROLE
- Analyze strategic risks, deterrence, and stability.
- Output a typed DECISION object.

OUTPUT SCHEMA
- decision_type: APPROVE (Safe/Beneficial), REJECT (Dangerous), MODIFY (Needs changes), ABORT (Critical Failure).
- recommended_action: Short action phrase.
- risk_score: 0 (Safe) to 10 (Critical).
- rationale_summary: Max 3 bullet points.


RISK CALIBRATION STANDARD (DO NOT DEVIATE)
0-2: Normal geopolitical friction.
3-4: Elevated tension (diplomatic pressure, sanctions).
5-6: Strategic competition with escalation signals.
7-8: Pre-crisis (military posture, economic warfare).
9-10: Active conflict (kinetic action, blockade).

PRINCIPLES
- Prefer restraint.
- If risk > 7, REJECT or ABORT.
- LOWER confidence if uncertain, do NOT inflate risk.
- Schema errors are system faults. Return ONLY valid JSON.
"""
