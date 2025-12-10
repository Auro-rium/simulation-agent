from typing import Any, Dict, List
from core.schemas import ConstraintResult
from agents.base_agent import BaseAgent

class ConstraintAgent(BaseAgent):
    def __init__(self):
        super().__init__("constraint")

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates and sanitizes the combined inputs from specialist agents.
        """
        specialist_outputs = inputs.get("specialist_outputs", {})
        
        prompt = f"""
        {CONSTRAINT_SYSTEM_PROMPT}
        
        ---
        SPECIALIST ASSESSMENTS:
        {specialist_outputs}
        """
        
        result = self.llm_client.generate_structured_output(
            prompt,
            response_schema=ConstraintResult.model_json_schema(),
            model_type="reasoning"
        )
        return {"constraint_check": result}

CONSTRAINT_SYSTEM_PROMPT = """You are CONSTRAINT_AGENT.

ROLE
- You are the moral, rule-based, and first-principles constraint checker.
- You DO NOT fully redesign strategies; you correct, prune, and constrain.

INPUT
- Bundled outputs from SECURITY_ANALYSIS_AGENT, TECHNOLOGY_ANALYSIS_AGENT, ECONOMICS_SPECIALIST_AGENT.
- Clear statement of Actor A's goals and any explicit constraints.

OUTPUT
Return:

{
  "ethical_flags": ["...", "..."],          // what might be morally problematic?
  "legal_or_policy_flags": ["...", "..."],  // generic, non-jurisdiction-specific
  "human_impact_analysis": ["...", "..."],  // likely impact on people, wellbeing
  "incoherence_or_contradictions": ["...", "..."],
  "required_modifications": ["...", "..."], // how to fix flagged issues
  "sanitized_recommendations_for_A": ["...", "..."]
}

PRINCIPLES
- Prioritize human wellbeing, safety, and non-harm.
- Avoid recommending or enabling real-world harm or unlawful actions.
- Enforce first-principles coherence: no magical thinking, no contradictions."""
