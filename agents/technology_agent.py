from typing import Any, Dict
from core.schemas import Decision, DecisionType
from agents.base_agent import BaseAgent

class TechnologyAgent(BaseAgent):
    def __init__(self):
        super().__init__("technology")

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        instruction = inputs.get("instruction")
        context = inputs.get("context", {})
        
        prompt = f"""
        {TECHNOLOGY_SYSTEM_PROMPT}

        ---
        SCENARIO CONTEXT: {context}
        SPECIFIC INSTRUCTION: {instruction}
        """
        
        result = await self.llm_client.generate_structured_output(
            prompt,
            response_schema=Decision.model_json_schema(),
            model="openai/gpt-oss-20b",
            max_tokens=200 # Strict cap
        )
        return {"decision": result}

TECHNOLOGY_SYSTEM_PROMPT = """You are TECHNOLOGY_ANALYSIS_AGENT.

ROLE
- Evaluate feasibility, timelines, and technical advantage.
- Output a typed DECISION object.

OUTPUT SCHEMA
- decision_type: APPROVE (Feasible), REJECT (Impossible/Too Risky), MODIFY (Needs R&D), ABORT.
- recommended_action: The technical path forward.
- risk_score: 0-10 (Failure risk).
- rationale_summary: Max 3 key technical constraints.


RISK CALIBRATION STANDARD (DO NOT DEVIATE)
0-2: Normal geopolitical friction.
3-4: Elevated tension (diplomatic pressure, sanctions).
5-6: Strategic competition with escalation signals.
7-8: Pre-crisis (military posture, economic warfare).
9-10: Active conflict (kinetic action, blockade).

PRINCIPLES
- Be realistic about timelines.
- Magic tech = ABORT.
- LOWER confidence if uncertain, do NOT inflate risk.
- Schema errors are system faults. Return ONLY valid JSON.
"""
