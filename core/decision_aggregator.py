from typing import List
from core.schemas import SpecialistDecision, CompositeDecision, Decision, DecisionType

class DecisionAggregator:
    """
    Deterministic component to merge specialist decisions.
    NO LLM. Pure logic.
    """
    
    @staticmethod
    @staticmethod
    def aggregate(specialist_decisions: List[SpecialistDecision]) -> CompositeDecision:
        # Filter buckets
        valid_sds = [sd for sd in specialist_decisions if sd.decision is not None]
        signals = [sd for sd in specialist_decisions if sd.signal is not None]
        faults = [sd for sd in specialist_decisions if sd.fault is not None]
        
        # --- DEGRADED MODE (Intelligence Salvage) ---
        if len(valid_sds) < 2 and signals:
            # "Compute risk as: base_risk + Σ inferred_risk_delta"
            base_risk = 0
            if valid_sds:
                base_risk = sum(sd.decision.risk_score for sd in valid_sds) / len(valid_sds)
            else:
                base_risk = 3 # Conservative baseline
                
            risk_delta = sum(s.signal.inferred_risk_delta for s in signals)
            final_risk = max(1, min(7, int(base_risk + risk_delta))) # Clamp [1, 7]
            
            # Synthesize Rationale
            rationale = []
            if valid_sds:
                 rationale.append(f"Primary: {valid_sds[0].decision.recommended_action}")
            
            for s in signals:
                 rationale.append(f"Signal ({s.agent}): {'; '.join(s.signal.summary_points)}")
            
            # Construct Composite
            return CompositeDecision(
                primary_decision=Decision(
                    decision_type=DecisionType.MODIFY,
                    recommended_action="Adaptive Response (Salvaged Intelligence)",
                    confidence=0.3 + (0.1 * len(signals)), # Proportional confidence
                    risk_score=final_risk,
                    rationale_summary=rationale[:3]
                ),
                conflicts=[],
                consensus_score=0.4, # Low consensus
                specialist_decisions=specialist_decisions
            )

        if not valid_sds:
            # "If zero Decisions exist (and no signals): status = DEGRADED_LLM... NOT ABORT"
             return CompositeDecision(
                primary_decision=Decision(
                    decision_type=DecisionType.MODIFY, # Conservative default
                    recommended_action="System Degraded: Proceeding with conservative baseline.",
                    confidence=0.0,
                    risk_score=0, # Neutral risk
                    rationale_summary=[f"Fault: {f.fault.message[:50]}..." for f in faults[:3]] or ["No Data"]
                ),
                conflicts=[],
                consensus_score=0.0,
                specialist_decisions=specialist_decisions
            )

        # --- RISK CALIPRATION ---
        # "If risks disagree -> choose the MEDIAN"
        risks = sorted([sd.decision.risk_score for sd in valid_sds])
        mid = len(risks) // 2
        median_risk = (risks[mid] + risks[~mid]) / 2
        
        # 2. Check for abort overrides (Safety First)
        # "ABORT allowed ONLY if: ≥2 independent... AND risk >= 8 AND confidence >= 0.6"
        abort_candidates = [sd for sd in valid_sds if sd.decision.decision_type == DecisionType.ABORT]
        
        valid_aborts = []
        for sd in abort_candidates:
             if sd.decision.risk_score >= 8 and sd.decision.confidence >= 0.6:
                 valid_aborts.append(sd)
        
        conflicts = []
        action_votes = {}
        rationale_pool = []
        assumptions_pool = []
        
        for sd in valid_sds:
            rationale_pool.extend([f"[{sd.agent}] {r}" for r in sd.decision.rationale_summary])
            assumptions_pool.extend(sd.decision.assumptions)
            act = sd.decision.recommended_action
            action_votes[act] = action_votes.get(act, 0) + 1

        # 3. Formulate Primary Decision
        if len(valid_aborts) >= 2:
            primary_type = DecisionType.ABORT
            primary_action = "Abort: Multiple validated critical failure signals"
            final_risk = max(sd.decision.risk_score for sd in valid_aborts)
            consensus = len(valid_aborts) / len(valid_sds)
        else:
            # Downgrade solo aborts or low-confidence aborts
            pass
            
        # Continue with standard logic if not aborted...
        if 'primary_type' not in locals():
            # Standard logic (Risk check, Majority vote)
            if final_risk >= 7:
                 primary_type = DecisionType.REJECT
            elif bias_approve:
                 primary_type = DecisionType.APPROVE
            else:
                 from collections import Counter
                 # If we have a single abort that we ignored, it's just one vote here
                 type_counts = Counter(types)
                 primary_type = type_counts.most_common(1)[0][0]

        candidates = [sd for sd in valid_sds if sd.decision.decision_type == primary_type]
        if not candidates:
             candidates = valid_sds 
             
        best_sd = min(candidates, key=lambda x: abs(x.decision.risk_score - final_risk))
        primary_action = best_sd.decision.recommended_action
        
        rationale = []
        for sd in valid_sds:
             rationale.append(f"[{sd.agent}] Risk {sd.decision.risk_score}: {sd.decision.rationale_summary[0] if sd.decision.rationale_summary else ''}")
        
        # Append fault warnings if any
        if faults:
            rationale.append(f"Warning: {len(faults)} agents incurred faults.")

        final_decision = Decision(
            decision_type=primary_type,
            recommended_action=primary_action,
            confidence=sum(sd.decision.confidence for sd in valid_sds) / len(valid_sds),
            risk_score=final_risk,
            rationale_summary=rationale[:3],
            assumptions=best_sd.decision.assumptions
        )
        
        return CompositeDecision(
            primary_decision=final_decision,
            conflicts=[],
            consensus_score=low_risk_count / len(valid_sds), 
            specialist_decisions=specialist_decisions # Return full list including faults for audit
        )
