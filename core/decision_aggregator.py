from typing import List
from core.schemas import SpecialistDecision, CompositeDecision, Decision, DecisionType

class DecisionAggregator:
    """
    Deterministic component to merge specialist decisions.
    NO LLM. Pure logic.
    """
    
    @staticmethod
    def aggregate(specialist_decisions: List[SpecialistDecision]) -> CompositeDecision:
        if not specialist_decisions:
            # Safe default fallback
            fallback_decision = Decision(
                decision_type=DecisionType.ABORT,
                recommended_action="No specialist input provided",
                confidence=0.0,
                risk_score=10,
                rationale_summary=["Input list was empty"]
            )
            return CompositeDecision(
                primary_decision=fallback_decision,
                conflicts=[],
                consensus_score=0.0,
                specialist_decisions=[]
            )

        # 1. Determine highest risk score
        max_risk = max(sd.decision.risk_score for sd in specialist_decisions)
        
        # 2. Check for abort overrides (Safety First)
        # If any specialist says ABORT or high risk (>=8), we tilt towards caution
        abort_signals = [sd for sd in specialist_decisions if sd.decision.decision_type == DecisionType.ABORT or sd.decision.risk_score >= 8]
        
        conflicts = []
        action_votes = {}
        rationale_pool = []
        assumptions_pool = []
        
        for sd in specialist_decisions:
            # Collect rationales
            rationale_pool.extend([f"[{sd.agent}] {r}" for r in sd.decision.rationale_summary])
            assumptions_pool.extend(sd.decision.assumptions)
            
            # Vote on actions (simple string match for now, assuming standardized actions usually, but here we just pick representative)
            act = sd.decision.recommended_action
            action_votes[act] = action_votes.get(act, 0) + 1

        # 3. Formulate Primary Decision
        if abort_signals:
            primary_type = DecisionType.ABORT
            primary_action = "Abort due to high risk signal: " + "; ".join([s.agent for s in abort_signals])
            # Use the highest risk
            final_risk = max_risk
            consensus = 0.0 # Forced overrides destroy consensus
        else:
            # Conservative consensus
            # If actions diverge, we might escalate.
            # For simplicity in logic: Pick the action with most votes, or the one from the 'lead' specialist logic if we had hierarchy.
            # Let's use simple Majority or First-Found.
            primary_action = max(action_votes, key=action_votes.get)
            primary_type = DecisionType.MODIFY # Default to modify unless strong approval
            
            # Calculate approval ratio
            approves = sum(1 for sd in specialist_decisions if sd.decision.decision_type == DecisionType.APPROVE)
            if approves == len(specialist_decisions):
                primary_type = DecisionType.APPROVE
            elif approves > len(specialist_decisions) / 2:
                primary_type = DecisionType.MODIFY
            else:
                primary_type = DecisionType.REJECT
                
            final_risk = max_risk
            consensus = len(set(action_votes.keys())) / len(specialist_decisions) # 1.0 = chaos, <1 = better agreement (inverted metric actually)
            # improved score:
            consensus = action_votes[primary_action] / len(specialist_decisions)

        # 4. Limit Text
        final_rationale = rationale_pool[:3] # strict cap

        final_decision = Decision(
            decision_type=primary_type,
            recommended_action=primary_action,
            confidence=sum(sd.decision.confidence for sd in specialist_decisions) / len(specialist_decisions),
            risk_score=final_risk,
            rationale_summary=final_rationale,
            assumptions=assumptions_pool[:5]
        )
        
        return CompositeDecision(
            primary_decision=final_decision,
            conflicts=conflicts, # Would populate if we did diff analysis
            consensus_score=consensus,
            specialist_decisions=specialist_decisions
        )
