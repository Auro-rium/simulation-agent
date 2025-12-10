from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class PartialEvent(BaseModel):
    """Event emitted by the worker thread to the UI."""
    type: str # 'progress', 'turn', 'constraint', 'synthesis', 'done', 'error'
    payload: Any = None
    index: Optional[int] = None
    text: Optional[str] = None
    
class TurnLog(BaseModel):
    """Structured log for a simulation turn."""
    turn_id: int
    actor: str
    action: str
    rationale: str
    timestamp: str

class EpisodeLog(BaseModel):
    """Complete log of a simulation run."""
    request: str
    plan: List[str]
    specialist_findings: Dict[str, Any]
    constraints: Dict[str, Any]
    simulation_history: List[Dict[str, Any]]
    final_report: str
