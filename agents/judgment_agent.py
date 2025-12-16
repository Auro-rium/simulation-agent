from typing import Dict, Any
from agents.base_agent import BaseAgent
from core.schemas import JudgmentResult, Decision, DecisionType

class JudgmentAgent(BaseAgent):
    def __init__(self):
        super().__init__("judgment")

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Final Arbiter. Outputs JudgmentResult containing final Decision.
        """
        composite_decision = inputs.get("composite_decision", {})
        constraint_result = inputs.get("constraint_output", {}) # ConstraintResult dict
        context = inputs.get("context", {})
        
        prompt = f"""
        {JUDGMENT_SYSTEM_PROMPT}
        
        ---
        SCENARIO CONTEXT: {context}
        
        COMPOSITE DECISION (from Specialists):
        {composite_decision}
        
        CONSTRAINT CHECK:
        {constraint_result}
        """
        
        result = await self.llm_client.generate_structured_output(
            prompt,
            response_schema=JudgmentResult.model_json_schema(),
            model="llama-3.3-70b-versatile"
        )
        
        return {"judgment_result": result}

JUDGMENT_SYSTEM_PROMPT = """You are JUDGMENT_AGENT.

ROLE
- You are the Final Decision Maker.
- You resolve trade-offs between Safety (Constraint) and Efficacy (Specialists).

INPUT
- CompositeDecision
- ConstraintResult (Output of Safety Check)

OUTPUT
- `JudgmentResult`
    - is_approved: bool
    - feedback: str (To Constraint Agent if REJECTED)
    - strategic_analysis: str
    - decision_type: APPROVE | REJECT | MODIFY | ESCALATE | ABORT
    - final_decision: `Decision` object (The authoritative action for Simulation)

LOGIC
- If Constraint.is_safe == False -> REJECT (Loop back) or ABORT.
- If Safe but Risk High -> MODIFY or ESCALATE.
- If Safe and Effective -> APPROVE.
"""
