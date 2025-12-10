import pytest
import asyncio
import os
import json
from unittest.mock import MagicMock, AsyncMock, patch
from orchestration.manager_run import manager_run
from core.schemas import Plan, Step, ConstraintResult

@pytest.fixture
def mock_agents():
    with patch("orchestration.graph.planner_agent") as mock_plan, \
         patch("orchestration.graph.constraint_agent") as mock_const, \
         patch.dict("orchestration.graph.specialists", values={
             "SECURITY": MagicMock(),
             "TECHNOLOGY": MagicMock(),
             "ECONOMICS": MagicMock()
         }) as mock_specs, \
         patch("orchestration.graph.llm_client") as mock_llm: # For simulation loop which is still raw LLM in graph
         
        # Setup mocks to match Agent.run() signatures (sync)
        mock_plan.run.return_value = {
            "plan": {
                 "steps": [
                     {"step_id": "S1", "task": "T1", "assigned_agent": "SECURITY"},
                     {"step_id": "S2", "task": "T2", "assigned_agent": "ECONOMICS"}
                 ]
            }
        }
        
        # Mock Specialists
        mock_specs["SECURITY"].run.return_value = {"analysis": "Security OK"}
        mock_specs["ECONOMICS"].run.return_value = {"analysis": "Econ OK"}
        
        # Mock Constraint
        mock_const.run.return_value = {
            "constraint_check": {
                "is_safe": True,
                "warnings": [],
                "sanitized_recommendations_for_A": []
            }
        }
        
        # Mock LLM for Simulation Loop (node_simulation_step) & Synthesis
        mock_llm.generate_with_retries = AsyncMock(return_value={"text": "Simulated Action", "meta": {}})
        
        yield {
            "planner": mock_plan,
            "constraint": mock_const,
            "specs": mock_specs,
            "llm": mock_llm
        }

@pytest.mark.asyncio
async def test_planner_called_once(mock_agents):
    await manager_run("Test Request", {})
    mock_agents["planner"].run.assert_called_once()

@pytest.mark.asyncio
async def test_parallel_specialists(mock_agents):
    # Retrieve mocks
    sec = mock_agents["specs"]["SECURITY"]
    econ = mock_agents["specs"]["ECONOMICS"]
    
    # Introduce delay to test parallelism
    def delayed_run(*args, **kwargs):
        import time
        time.sleep(0.5) 
        return {"analysis": "Done"}
        
    sec.run.side_effect = delayed_run
    econ.run.side_effect = delayed_run
    
    import time
    start = time.time()
    # max_turns=0 to skip simulation
    await manager_run("Parallel Test", {"max_turns": 0}) 
    duration = time.time() - start
    
    # If serial: 0.5 + 0.5 = 1.0s. If parallel: ~0.5s.
    assert duration < 0.9, f"Specialists took {duration}s, expected <0.9s (Parallel)"

@pytest.mark.asyncio
async def test_streaming_callback(mock_agents):
    events = []
    def callback(e):
        events.append(e)
        
    await manager_run("Stream Test", {}, progress_callback=callback)
    
    event_types = [e["type"] for e in events]
    assert "status" in event_types
    assert "plan" in event_types
    assert "specialist_done" in event_types
    assert "constraint" in event_types
    # Simulation turn events (default max_turns=3 so loop runs)
    assert "turn" in event_types
    assert "done" in event_types

@pytest.mark.asyncio
async def test_persistence(mock_agents):
    res = await manager_run("Persistence Test", {})
    run_id = res.get("run_id")
    assert run_id
    assert os.path.exists(f"runs/{run_id}.json")
    if os.path.exists(f"runs/{run_id}.json"):
        os.remove(f"runs/{run_id}.json")
