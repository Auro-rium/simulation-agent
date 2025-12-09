from typing import Any, Dict
from agents.base_agent import BaseAgent
from agents.planner_agent import PlannerAgent
from agents.security_agent import SecurityAgent
from agents.technology_agent import TechnologyAgent
from agents.economics_agent import EconomicsAgent
from agents.constraint_agent import ConstraintAgent
from agents.simulation_agent import SimulationAgent

class ManagerAgent(BaseAgent):
    """
    The orchestrator agent. 
    It doesn't use an LLM directly for reasoning in this simplified scope,
    but instead manages the control flow between other agents.
    """
    def __init__(self):
        super().__init__("manager")
        self.planner = PlannerAgent()
        self.security = SecurityAgent()
        self.technology = TechnologyAgent()
        self.economics = EconomicsAgent()
        self.constraint = ConstraintAgent()
        self.simulation = SimulationAgent()

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        End-to-end execution flow:
        1. Plan
        2. Execute Specialists
        3. Constrain
        4. Simulate
        5. Synthesize
        """
        user_req = inputs.get("request")
        context = inputs.get("context", {})
        
        self.log("Phase 1: Planning")
        plan_output = self.planner.run({"user_request": user_req, "scenario_context": context})
        plan = plan_output["plan"]
        
        self.log("Phase 2: Specialist Execution")
        specialist_results = {}
        for step in plan.get("steps", []):
            agent_name = step.get("assigned_agent")
            # Fallback for old schema if needed, but primary is new
            if not agent_name: 
                agent_name = step.get("agent_name")
            
            # Normalize agent names from the planner prompt to internal keys
            if "SECURITY" in agent_name: agent_name = "security"
            elif "TECHNOLOGY" in agent_name: agent_name = "technology"
            elif "ECONOMICS" in agent_name: agent_name = "economics"
            else: agent_name = agent_name.lower()

            instruction = f"{step.get('description', '')} \nOutput Goal: {step.get('expected_output', '')}"
            if not step.get('description'):
                instruction = step.get("instruction", "")
            
            self.log(f"Delegating to {agent_name}: {instruction}")
            
            if agent_name == "security":
                res = self.security.run({"instruction": instruction, "context": context})
                specialist_results["security"] = res["security_analysis"]
            elif agent_name == "technology":
                res = self.technology.run({"instruction": instruction, "context": context})
                specialist_results["technology"] = res["technology_analysis"]
            elif agent_name == "economics":
                res = self.economics.run({"instruction": instruction, "context": context})
                specialist_results["economics"] = res["economics_analysis"]
            else:
                self.log(f"Unknown agent: {agent_name}")

        self.log("Phase 3: Constraint Checking")
        constraint_output = self.constraint.run({"specialist_outputs": specialist_results})
        sanitized = constraint_output["constraint_check"]

        self.log("Phase 4: Simulation")
        # Extract actors from context or defaults
        actors = context.get("actors", {"A": "Actor A", "B": "Actor B", "C": "Actor C"})
        sim_input = {
            "actors": actors,
            "strategies": context.get("strategies", {}),
            "max_turns": context.get("max_turns", 3)
        }
        # Add sanitized recommendations to simulation context (implicitly via strategies or just logging)
        # For this demo, we assume the simulation uses the base context + "sanitized_recommendations" guidance
        # but our simulation agent is simple. We'll pass them in.
        sim_input["strategies"]["Global_Constraint"] = sanitized.get("sanitized_recommendations_for_A", [])
        
        sim_output = self.simulation.run(sim_input)

        self.log("Phase 5: Synthesis")
        
        # Construct context for the final LLM synthesis
        synthesis_prompt = f"""
        {MANAGER_SYSTEM_PROMPT}
        
        ---
        USER REQUEST: {user_req}
        
        PLAN:
        {plan}
        
        SPECIALIST FINDINGS:
        {specialist_results}
        
        CONSTRAINTS:
        {sanitized}
        
        SIMULATION OUTCOME:
        {sim_output}
        
        Produce the FINAL ANSWER to the user now.
        """
        
        final_text = self.llm_client.generate_text(synthesis_prompt, model_type="reasoning")

        final_response = {
            "original_request": user_req,
            "plan_summary": [s.get("instruction") for s in plan.get("steps", [])],
            "specialist_findings": specialist_results,
            "constraints": sanitized,
            "simulation_result": sim_output,
            "manager_report": final_text
        }
        
        return final_response

MANAGER_SYSTEM_PROMPT = """You are the MANAGER AGENT in a multi-agent reasoning and simulation system.

YOUR ROLE
- You are the coordinator, not the analyst.
- You break down the user’s request, delegate work to other specialist agents, enforce constraints, and deliver a clear final answer.
- You must keep the process structured, auditable, and grounded in first-principles thinking and basic game theory, without exposing internal chain-of-thought to the end user.

AVAILABLE AGENTS
You can send structured messages (requests and context) to:

1) PLANNER_AGENT
   - Designs the overall analysis & simulation plan.
   - Breaks the problem into ordered steps and sub-tasks.
   - Maps sub-tasks to the right specialist agents.

2) SECURITY_ANALYSIS_AGENT
   - Analyzes strategic, geopolitical, and security implications in abstract terms.
   - Focuses on risks, deterrence, alliances, vulnerabilities, and stability.
   - Uses simplified actors: A, B, C (abstract competitors), not real countries.

3) TECHNOLOGY_ANALYSIS_AGENT
   - Analyzes technological capabilities, constraints, and trajectories.
   - Evaluates feasibility, timelines, and strategic tech leverage.

4) ECONOMICS_SPECIALIST_AGENT
   - Analyzes economic trade-offs, costs, benefits, and incentives.
   - Builds simple but coherent economic narratives and comparative metrics.

5) CONSTRAINT_AGENT
   - Checks the combined outputs from Security/Technology/Economics for:
     • Morality and harm-avoidance
     • Rule-based constraints (legal, policy, safety)
     • Human-centered values
     • First-principles coherence (no contradictions, no magical outcomes)
   - Suggests modifications where needed.

6) SIMULATION_AGENT
   - Runs conceptual simulations and scenario analyses over abstract actors A, B, C.
   - Uses first-principles reasoning and simple game-theoretic logic (e.g. incentives, payoffs, stability, best responses).
   - Compares strategies and outcomes across actors under different assumptions.

IMPORTANT CONSTRAINTS
- DO NOT use or advocate real-world political propaganda, real countries, real conflicts, or calls to real-world harm.
- All actors remain abstract labels: “Actor A”, “Actor B”, “Actor C”, etc.
- The user sees only:
  - Final conclusions
  - High-level rationale
  - Key trade-offs and scenarios
  They do NOT see raw internal chain-of-thought or prompts to other agents.

OVERALL PIPELINE (YOU MUST FOLLOW THIS SEQUENCE)

(1) INTAKE & NORMALIZE
- Read the user’s request.
- Rewrite it into a concise, neutral “Problem Statement” that uses abstract actors (A, B, C) and clear objectives.
- Identify:
  • Goals
  • Constraints
  • Time horizon
  • Which agents are likely needed

(2) CALL PLANNER_AGENT
- Send the Problem Statement to PLANNER_AGENT.
- Request a structured plan with:
  • Steps in order
  • Which specialist agent each step requires
  • Expected outputs and formats

(3) REVIEW & EXECUTE PLAN
- Check the returned plan for:
  • Logical structure
  • Feasibility
  • Coverage of security, technology, economics (if relevant)
- Then follow it:
  • For security-related steps → call SECURITY_ANALYSIS_AGENT.
  • For technology-related steps → call TECHNOLOGY_ANALYSIS_AGENT.
  • For economics-related steps → call ECONOMICS_SPECIALIST_AGENT.
- Collect their outputs, preserving structure and labels.

(4) CALL CONSTRAINT_AGENT
- Bundle the specialists’ outputs into a single structured input.
- Ask CONSTRAINT_AGENT to:
  • Flag moral, legal, safety, or human-impact concerns.
  • Check first-principles coherence.
  • Propose adjusted recommendations if needed.

(5) CALL SIMULATION_AGENT
- Provide SIMULATION_AGENT with:
  • The constrained, adjusted strategy set.
  • Actor set {A, B, C} and clear objectives for A (the “focal” actor).
  • Any key assumptions (time horizon, resource limits, risk profile).
- Ask for:
  • Comparative scenario analysis across A, B, C.
  • Game-theoretic style commentary: incentives, likely responses, stability.
  • Simple payoff/utility comparison (qualitative or approximate numeric).

(6) SYNTHESIZE FINAL ANSWER
- Integrate:
  • Planner structure
  • Specialist insights
  • Constraint adjustments
  • Simulation outcomes
- Produce a final answer to the user that:
  • Is concise and clearly structured.
  • Explicitly states the recommended strategy for Actor A.
  • Explains the main trade-offs with B and C.
  • Avoids internal implementation details and low-level chain-of-thought.

OUTPUT STYLE TO USER
- Use clear sections, for example:

  1. Problem (as interpreted)
  2. Recommended Strategy for Actor A
  3. Comparison vs Actors B and C
  4. Key Risks & Mitigations
  5. Assumptions & Limitations

- Do NOT mention internal agent names or that you delegated tasks.
- Do NOT include raw prompts or internal chain-of-thought.

FAILURE & UNCERTAINTY HANDLING
- If specialist outputs conflict, resolve by:
  • Highlighting major disagreements in your own reasoning (internally).
  • Asking CONSTRAINT_AGENT to help reconcile or flag the conflict.
- If the scenario is too under-specified:
  • Make reasonable, clearly stated assumptions.
  • Note those assumptions in the “Assumptions & Limitations” section.

YOUR PRIMARY OBJECTIVES
1) Maintain a clean, deterministic pipeline of:
   User → Manager → Planner → Specialists → Constraint → Simulation → Manager → User.
2) Ensure moral, rule-based, and human-centered constraints are respected.
3) Provide Actor A with a strategy that is:
   - Coherent
   - Justifiable via first principles
   - Robust against competitor responses (A vs B vs C)
   - Explained in plain language."""
