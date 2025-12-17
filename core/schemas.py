from typing import Any, Dict, List, Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import uuid

# --- Enums ---

class DecisionType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MODIFY = "MODIFY"
    ESCALATE = "ESCALATE"
    ABORT = "ABORT"

class ExecutionPhase(str, Enum):
    INIT = "INIT"
    RUNNING = "RUNNING"
    FINALIZING = "FINALIZING"

class RunStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    DEGRADED_LLM = "DEGRADED_LLM"
    CONSTRAINT_BLOCKED = "CONSTRAINT_BLOCKED"
    SIMULATION_INVALID = "SIMULATION_INVALID"
    SYSTEM_ERROR = "SYSTEM_ERROR"

# --- Structured Outputs ---

class Decision(BaseModel):
    decision_type: DecisionType
    recommended_action: str
    confidence: float = Field(..., ge=0, le=1)
    risk_score: int = Field(..., ge=0, le=10)
    rationale_summary: List[str] = Field(max_length=3)
    assumptions: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)

# Agent-Specific Schemas (Inherit from Decision for consistency)
class SecurityAssessment(Decision):
    pass

class EconAssessment(Decision):
    pass

# Replaces SpecialistOutput but keeps some compatibility or wrapping
class AgentFault(BaseModel):
    fault_type: Literal["SCHEMA_ERROR", "TIMEOUT", "RATE_LIMIT", "SYSTEM_ERROR"]
    agent: str
    step_id: str
    message: str

class IntelligenceSignal(BaseModel):
    """Fallback for schema-invalid but semantically useful output."""
    source_agent: str
    summary_points: List[str] = Field(..., max_length=3)
    confidence: float
    inferred_risk_delta: int = Field(..., ge=-2, le=2)

class SpecialistDecision(BaseModel):
    agent: str
    decision: Optional[Decision] = None
    fault: Optional[AgentFault] = None
    signal: Optional[IntelligenceSignal] = None
    thought_trace: Optional[str] = None # For UI "Thinking" display
    raw_output: Optional[Dict[str, Any]] = None # For debugging/logging
    meta: Dict[str, Any] = Field(default_factory=dict)

class CompositeDecision(BaseModel):
    primary_decision: Decision
    conflicts: List[str] = Field(default_factory=list)
    consensus_score: float
    specialist_decisions: List[SpecialistDecision]

# --- Plan ---

class PlanStep(BaseModel):
    step_id: str
    agent: str
    objective: str
    priority: int = 1

class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    steps: List[PlanStep]
    context: Dict[str, Any] = Field(default_factory=dict)

# --- Simulation ---

class ValidationResult(BaseModel):
    valid: bool
    violation: Optional[str] = None

class SimulationTurn(BaseModel):
    turn: int
    actor: str
    action: str
    outcome: str
    validation: ValidationResult
    meta: Dict[str, Any] = Field(default_factory=dict)

class ConstraintResult(BaseModel):
    is_safe: bool
    warnings: List[str] = Field(default_factory=list)
    sanitized_output: Optional[Dict[str, Any]] = None
    reasoning: Optional[str] = None
    ethical_flags: List[str] = Field(default_factory=list)
    legal_flags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    feedback_from_judgment: Optional[str] = None

class JudgmentResult(BaseModel):
    is_approved: bool
    feedback: str
    strategic_analysis: str
    decision_type: Optional[DecisionType] = None
    final_decision: Optional[Decision] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class SimulationResult(BaseModel):
    simulation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    final_state: Dict[str, Any]
    outcome: str
    stability_score: float = Field(..., ge=0, le=1)
    turn_count: int
    history: List[SimulationTurn]
    meta: Dict[str, Any] = Field(default_factory=dict)

# --- Final ---

class FinalReport(BaseModel):
    run_id: str
    status: RunStatus
    final_decision: Decision
    simulation_result: Optional[SimulationResult]
    audit_trail: Dict[str, Any]
    timestamps: Dict[str, str]

# Helper for validation
def validate_schema(data: Any, schema_model: BaseModel):
    return schema_model.model_validate(data)
