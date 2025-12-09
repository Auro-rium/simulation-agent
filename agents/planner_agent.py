from typing import List, Any, Dict
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class PlanStep(BaseModel):
    step_id: str
    assigned_agent: str = Field(description="One of: SECURITY_ANALYSIS_AGENT, TECHNOLOGY_ANALYSIS_AGENT, ECONOMICS_SPECIALIST_AGENT")
    description: str
    expected_output: str

class Plan(BaseModel):
    high_level_goal: str
    assumptions: List[str]
    steps: List[PlanStep]

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__("planner")

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the user request and scenario to produce an execution plan.
        Inputs:
            - user_request: str
            - scenario_context: Dict
        """
        user_req = inputs.get("user_request")
        context = inputs.get("scenario_context")
        
        self.log(f"Planning for request: {user_req}")
        
        prompt = f"""
        {PLANNER_SYSTEM_PROMPT}
        
        ---
        PROBLEM STATEMENT / REQUEST: 
        {user_req}
        
        CONTEXT: 
        {context}
        """
        
        try:
            plan_data = self.llm_client.generate_structured_output(
                prompt,
                response_schema=Plan.model_json_schema(),
                model_type="reasoning"
            )
            self.log(f"Plan generated with {len(plan_data.get('steps', []))} steps.")
            return {"plan": plan_data}
        except Exception as e:
            self.log(f"Planning failed: {e}")
            raise

PLANNER_SYSTEM_PROMPT = """You are PLANNER_AGENT.

ROLE
- You do NOT solve the problem directly.
- You design an ordered plan that other specialist agents will execute.

INPUT
- A “Problem Statement” with abstract actors (A, B, C) and goals for Actor A.

OUTPUT
Return a structured plan in this shape:

{
  "high_level_goal": "...",
  "assumptions": ["...", "..."],
  "steps": [
    {
      "step_id": "S1",
      "description": "...",
      "assigned_agent": "SECURITY_ANALYSIS_AGENT",
      "expected_output": "Describe security risks, opportunities, and recommended posture for Actor A vs B, C."
    },
    {
      "step_id": "S2",
      "description": "...",
      "assigned_agent": "TECHNOLOGY_ANALYSIS_AGENT",
      "expected_output": "Describe key technologies, feasibility, and leverage points."
    },
    {
      "step_id": "S3",
      "description": "...",
      "assigned_agent": "ECONOMICS_SPECIALIST_AGENT",
      "expected_output": "Describe economic costs, benefits, and incentive compatibility."
    }
    // Add more steps if necessary
  ]
}

GUIDING PRINCIPLES
- Think in first principles: clarify objectives, constraints, resources, and feedback loops.
- Be explicit about what each specialist should produce and in what format.
- Keep the number of steps minimal but sufficient."""
