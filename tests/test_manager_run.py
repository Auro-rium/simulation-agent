import pytest
import asyncio
import os
from unittest.mock import AsyncMock, patch
from orchestration.manager_run import manager_run
from core.schemas import ExecutionPlan, RunStatus, Decision, DecisionType

@pytest.fixture
def mock_agents():
    with patch("orchestration.graph.PlannerAgent") as MockPlannerCls, \
         patch("orchestration.graph.ConstraintAgent") as MockConstraintCls, \
         patch("orchestration.graph.JudgmentAgent") as MockJudgmentCls, \
         patch("orchestration.graph.SecurityAgent") as MockSecCls, \
         patch("orchestration.graph.TechnologyAgent") as MockTechCls, \
         patch("orchestration.graph.EconomicsAgent") as MockEconCls, \
         patch("orchestration.graph.SimulationAgent") as MockSimCls:
         
        mock_planner = AsyncMock()
        MockPlannerCls.return_value = mock_planner
        
        mock_planner.run.return_value = {
            "plan": {
                 "plan_id": "test-plan",
                 "steps": [{"step_id": "1", "agent": "SECURITY", "objective": "Analyze"}],
                 "context": {}
            }
        }

        mock_sec = AsyncMock()
        MockSecCls.return_value = mock_sec
        # Valid Decision object dict
        mock_sec.run.return_value = {
            "decision": {
                "decision_type": "APPROVE",
                "recommended_action": "Fortify",
                "confidence": 0.9,
                "risk_score": 2,
                "rationale_summary": ["Safe"],
                "assumptions": []
            }
        }
        
        mock_constraint = AsyncMock()
        MockConstraintCls.return_value = mock_constraint
        mock_constraint.run.return_value = {
            "constraint_check": {
                "is_safe": True,
                "warnings": []
            }
        }
        
        mock_judgment = AsyncMock()
        MockJudgmentCls.return_value = mock_judgment
        mock_judgment.run.return_value = {
            "judgment_result": {
                "is_approved": True,
                "feedback": "",
                "strategic_analysis": "Good",
                "final_decision": {
                    "decision_type": "APPROVE",
                    "recommended_action": "Fortify",
                    "confidence": 0.9,
                    "risk_score": 2,
                    "rationale_summary": ["Safe"],
                    "assumptions": []
                }
            }
        }
        
        mock_sim = AsyncMock()
        MockSimCls.return_value = mock_sim
        mock_sim.run.return_value = {
            "simulation_turn": {
                "turn": 1,
                "actor": "Actor A",
                "action": "Fortify",
                "outcome": "Done",
                "validation": {"valid": True}
            }
        }

        yield

@pytest.mark.asyncio
async def test_full_run_v0_3_0(mock_agents):
    events = []
    def callback(e):
        events.append(e)
        
    result = await manager_run("Test", {}, progress_callback=callback)
    
    assert result["status"] == RunStatus.SUCCESS
    assert "final_decision" in result
    
    event_types = [e["type"] for e in events]
    assert "plan" in event_types
    assert "composite" in event_types
    assert "judgment" in event_types
    assert "simulation" in event_types
    assert "done" in event_types
