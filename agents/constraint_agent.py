from typing import Any, Dict, List
from core.schemas import ConstraintResult, CompositeDecision, Decision, DecisionType
from agents.base_agent import BaseAgent

class ConstraintAgent(BaseAgent):
    def __init__(self):
        super().__init__("constraint")

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the CompositeDecision from DecisionAggregator.
        """
        composite_decision = inputs.get("composite_decision", {}) # Dict or Pydantic
        
        prompt = f"""
        {CONSTRAINT_SYSTEM_PROMPT}
        
        ---
        COMPOSITE DECISION (from Specialists):
        {composite_decision}
        
        PREVIOUS JUDGMENT FEEDBACK (If any - Address this):
        {inputs.get('judgment_feedback', 'None')}
        """
        
        result = await self.llm_client.generate_structured_output(
            prompt,
            response_schema=ConstraintResult.model_json_schema(),
            model="llama-3.3-70b-versatile"
        )
        return {"constraint_check": result}

CONSTRAINT_SYSTEM_PROMPT = """You are CONSTRAINT_AGENT.

ROLE
- You are the Safety & Compliance Officer.
- You validate the `CompositeDecision` proposed by specialists.
- You DO NOT formulate strategy. You PASS or FAIL it.

INPUT
- a `CompositeDecision` object.

OUTPUT
- `ConstraintResult`
    - is_safe: bool
    - ethical_flags: list[str]
    - legal_flags: list[str]
    - warnings: list[str]
    - sanitized_output: (Optional) A safer version of the Decision if minor tweaks work.
    - retry_count: (Passthrough)
    - feedback_from_judgment: (Passthrough)

PRINCIPLES
- If risk_score > 8, FAIL immediately.
- If illegal (Geneva Convention, etc.), FAIL.
- If valid but risky, PASS with warnings.
"""
