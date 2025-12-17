from typing import List, Any, Dict
from core.schemas import ExecutionPlan
from agents.base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("planner")

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce a strict ExecutionPlan. 
        """
        req = inputs["user_request"]
        ctx = inputs["scenario_context"]
        
        prompt = f"""
        {PLANNER_SYSTEM_PROMPT}
        
        REQUEST: {req}
        CONTEXT: {ctx}
        """
        
        try:
            result = await self.llm_client.generate_structured_output(
                prompt,
                response_schema=ExecutionPlan.model_json_schema(),
                model="openai/gpt-oss-120b",
                max_tokens=300 # Strict cap
            )
            return {"plan": result}
        except Exception as e:
            self.log(f"Planning failed: {e}")
            raise e

PLANNER_SYSTEM_PROMPT = """You are PLANNER_AGENT.

ROLE
- You convert abstract requests into a concrete EXECUTION PLAN.
- You run ONCE.

OUTPUT
- JSON matching `ExecutionPlan`.
- `steps`: List of `PlanStep` items.
    - `agent`: Must be one of [SECURITY, ECONOMICS, TECHNOLOGY].
    - `objective`: Concise task.
    - `priority`: 1 (High) to 5 (Low).

RULES
- NO prose.
- NO explanations.
- Decompose complex requests into parallel specialist tasks.
"""
