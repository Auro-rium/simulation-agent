import uuid
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class Step(BaseModel):
    step_id: str
    task: str
    assigned_agent: str
    description: Optional[str] = None
    expected_output: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

class Plan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    high_level_goal: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)
    steps: List[Step]
    final_step: str = "SIMULATION"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SpecialistOutput(BaseModel):
    agent: str
    step_id: str
    output: Dict[str, Any]
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('output')
    @classmethod
    def validate_output_not_empty(cls, v):
        if not v:
            raise ValueError("Specialist output cannot be empty")
        return v

class ConstraintResult(BaseModel):
    is_safe: bool
    warnings: List[str] = Field(default_factory=list)
    sanitized_output: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    # Richer fields from ConstraintAgent
    ethical_flags: List[str] = Field(default_factory=list)
    legal_flags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)

class SimulationTurn(BaseModel):
    turn: int
    actor: str
    action: str
    result: str
    meta: Dict[str, Any] = Field(default_factory=dict, description="Tracing info")

class SimulationResult(BaseModel):
    simulation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    simulation_history: List[SimulationTurn] = Field(default_factory=list)
    outcomes: Dict[str, Any] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)

class FinalReport(BaseModel):
    run_id: str
    request: str
    plan: Plan
    specialist_outputs: List[SpecialistOutput]
    constraint_result: ConstraintResult
    simulation_result: SimulationResult
    manager_report: str
    status: Literal["completed", "failed", "degraded"] = "completed"
    timestamps: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Global run metadata (e.g. seed)")

# Helper
def validate_schema(data: Any, schema_model: BaseModel):
    return schema_model.model_validate(data)
