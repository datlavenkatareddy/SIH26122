"""
Phase 2 Impact Preview A1 Core Constraint Engine.

Pure, deterministic evaluation of schedule relationship constraints (FS, SS, FF, SF),
lag/lead, cross-dimension reconciliation on REQUIRED SUCCESSOR START, controlling constraint
selection with deterministic tie-breaking, float absorption, and execution-state gating.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.shared.schemas import ExecutionState


def parse_date(val: Any) -> Optional[date]:
    """Parse a date from string, date, or datetime object."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@dataclass
class ConstraintEvaluation:
    predecessor_activity_id: str
    successor_activity_id: str
    relationship_type: str
    lag_days: float
    constraint_dimension: str  # "START" or "FINISH"
    required_successor_start: Optional[date] = None
    required_successor_finish: Optional[date] = None
    baseline_successor_start: Optional[date] = None
    gross_delay_days: int = 0
    is_controlling: bool = False
    uncertainty: bool = False
    uncertainty_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predecessor_activity_id": self.predecessor_activity_id,
            "successor_activity_id": self.successor_activity_id,
            "relationship_type": self.relationship_type,
            "lag_days": self.lag_days,
            "constraint_dimension": self.constraint_dimension,
            "required_successor_start": self.required_successor_start.isoformat() if self.required_successor_start else None,
            "required_successor_finish": self.required_successor_finish.isoformat() if self.required_successor_finish else None,
            "baseline_successor_start": self.baseline_successor_start.isoformat() if self.baseline_successor_start else None,
            "gross_delay_days": self.gross_delay_days,
            "is_controlling": self.is_controlling,
            "uncertainty": self.uncertainty,
            "uncertainty_reason": self.uncertainty_reason,
        }


def evaluate_constraint(
    *,
    predecessor_id: str,
    predecessor_start: Optional[date],
    predecessor_finish: Optional[date],
    successor_id: str,
    successor_planned_start: Optional[date],
    successor_planned_finish: Optional[date],
    relationship_type: str,
    lag_days: float = 0.0,
    is_target_predecessor: bool = False,
    simulated_delay_days: int = 0,
) -> ConstraintEvaluation:
    """
    Evaluate a single predecessor constraint against a successor.
    
    For a predecessor participating in a downstream propagation step (target or intermediate),
    its relevant constraint dates are its baseline planned dates shifted by its currently
    selected propagated net delay:
        simulated_pred_start = predecessor_start + timedelta(days=pred_delay)
        simulated_pred_finish = predecessor_finish + timedelta(days=pred_delay)
    
    Convert FF/SF finish constraints to required successor start using successor planned duration.
    """
    rel = relationship_type.strip().upper() if relationship_type else "FS"
    
    # Calculate simulated predecessor dates
    # For any participating predecessor (target or downstream), dates are shifted by simulated_delay_days
    pred_delay = simulated_delay_days if (simulated_delay_days or is_target_predecessor) else 0
    simulated_pred_start = predecessor_start + timedelta(days=pred_delay) if predecessor_start else None
    simulated_pred_finish = predecessor_finish + timedelta(days=pred_delay) if predecessor_finish else None
    
    lag_delta = timedelta(days=lag_days)
    
    # Calculate successor planned duration
    succ_duration: Optional[int] = None
    if successor_planned_start and successor_planned_finish:
        succ_duration = (successor_planned_finish - successor_planned_start).days
        
    evaluation = ConstraintEvaluation(
        predecessor_activity_id=predecessor_id,
        successor_activity_id=successor_id,
        relationship_type=rel,
        lag_days=lag_days,
        constraint_dimension="START",
        baseline_successor_start=successor_planned_start,
    )
    
    if rel == "FS":
        evaluation.constraint_dimension = "START"
        if simulated_pred_finish is not None:
            evaluation.required_successor_start = simulated_pred_finish + lag_delta
        else:
            evaluation.uncertainty = True
            evaluation.uncertainty_reason = f"Predecessor {predecessor_id} missing finish date"
            
    elif rel == "SS":
        evaluation.constraint_dimension = "START"
        if simulated_pred_start is not None:
            evaluation.required_successor_start = simulated_pred_start + lag_delta
        else:
            evaluation.uncertainty = True
            evaluation.uncertainty_reason = f"Predecessor {predecessor_id} missing start date"
            
    elif rel == "FF":
        evaluation.constraint_dimension = "FINISH"
        if simulated_pred_finish is not None:
            evaluation.required_successor_finish = simulated_pred_finish + lag_delta
            if succ_duration is not None:
                evaluation.required_successor_start = evaluation.required_successor_finish - timedelta(days=succ_duration)
            else:
                evaluation.uncertainty = True
                evaluation.uncertainty_reason = f"Successor {successor_id} missing planned duration for FF conversion"
        else:
            evaluation.uncertainty = True
            evaluation.uncertainty_reason = f"Predecessor {predecessor_id} missing finish date"
            
    elif rel == "SF":
        evaluation.constraint_dimension = "FINISH"
        if simulated_pred_start is not None:
            evaluation.required_successor_finish = simulated_pred_start + lag_delta
            if succ_duration is not None:
                evaluation.required_successor_start = evaluation.required_successor_finish - timedelta(days=succ_duration)
            else:
                evaluation.uncertainty = True
                evaluation.uncertainty_reason = f"Successor {successor_id} missing planned duration for SF conversion"
        else:
            evaluation.uncertainty = True
            evaluation.uncertainty_reason = f"Predecessor {predecessor_id} missing start date"
            
    else:
        evaluation.uncertainty = True
        evaluation.uncertainty_reason = f"Unsupported relationship type '{rel}'"
        
    if evaluation.required_successor_start is not None and successor_planned_start is not None:
        evaluation.gross_delay_days = max(0, (evaluation.required_successor_start - successor_planned_start).days)
    else:
        evaluation.gross_delay_days = 0
        
    return evaluation


def compare_constraints(c1: ConstraintEvaluation, c2: ConstraintEvaluation) -> int:
    """
    Deterministic tie-break comparator for constraints.
    Returns:
       1 if c1 is controlling over c2
      -1 if c2 is controlling over c1
       0 if identical
       
    Rules (docs/phase2_a1_contract.md Section 3.2):
    1. Latest required_successor_start
    2. Larger gross_delay_days
    3. predecessor_activity_id ascending (lexicographical)
    4. relationship_type ascending
    """
    # 1. Latest required_successor_start
    if c1.required_successor_start != c2.required_successor_start:
        if c1.required_successor_start is None:
            return -1
        if c2.required_successor_start is None:
            return 1
        return 1 if c1.required_successor_start > c2.required_successor_start else -1
        
    # 2. Larger gross_delay_days
    if c1.gross_delay_days != c2.gross_delay_days:
        return 1 if c1.gross_delay_days > c2.gross_delay_days else -1
        
    # 3. predecessor_activity_id ascending
    if c1.predecessor_activity_id != c2.predecessor_activity_id:
        return 1 if c1.predecessor_activity_id < c2.predecessor_activity_id else -1
        
    # 4. relationship_type ascending
    if c1.relationship_type != c2.relationship_type:
        return 1 if c1.relationship_type < c2.relationship_type else -1
        
    return 0


def select_controlling_constraint(constraints: List[ConstraintEvaluation]) -> Optional[ConstraintEvaluation]:
    """
    Select the single controlling constraint among all evaluated constraints.
    """
    valid = [c for c in constraints if c.required_successor_start is not None]
    if not valid:
        return None
    return max(valid, key=functools.cmp_to_key(compare_constraints))


def evaluate_successor_impact(
    *,
    successor: Dict[str, Any],
    execution_state: str,
    constraints: List[ConstraintEvaluation],
    target_activity_id: str,
    propagation_depth: int = 1,
    target_path: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Evaluate impact on an affected successor given all its evaluated incoming constraints.
    
    Applies:
    - Execution state gating: COMPLETED successor -> impact = 0, no shift.
    - Controlling constraint selection.
    - Gross delay relative to successor baseline planned start.
    - Float absorption contract (NULL float -> UNKNOWN, otherwise calculate absorbed and net delay).
    """
    succ_id = str(successor.get("activity_id"))
    baseline_start = parse_date(successor.get("planned_start"))
    baseline_finish = parse_date(successor.get("planned_finish"))
    raw_float = successor.get("total_float")
    
    uncertainty = any(c.uncertainty for c in constraints)
    
    controlling = select_controlling_constraint(constraints)
    if controlling:
        controlling.is_controlling = True
        
    is_completed = (execution_state == ExecutionState.COMPLETED.value or execution_state == "COMPLETED")
    
    if is_completed:
        gross_delay_days = 0
        shifted_start = baseline_start
        absorbed_delay_days: Optional[int] = 0
        net_delay_days: Optional[int] = 0
        float_status = "KNOWN" if raw_float is not None else "UNKNOWN"
        classification = "ALREADY_COMPLETED"
    else:
        if controlling is not None and baseline_start is not None and controlling.required_successor_start is not None:
            gross_delay_days = max(0, (controlling.required_successor_start - baseline_start).days)
            shifted_start = baseline_start + timedelta(days=gross_delay_days)
        else:
            gross_delay_days = 0
            shifted_start = baseline_start
            if controlling is None:
                uncertainty = True
                
        # Float evaluation
        if raw_float is None:
            float_status = "UNKNOWN"
            absorbed_delay_days = None
            net_delay_days = None
            uncertainty = True
        else:
            float_status = "KNOWN"
            float_val = float(raw_float)
            absorbed_delay_days = int(min(max(gross_delay_days, 0), max(float_val, 0.0)))
            net_delay_days = int(max(gross_delay_days - max(float_val, 0.0), 0.0))
            
        # Classification
        if controlling is not None and controlling.predecessor_activity_id != target_activity_id and gross_delay_days == 0:
            classification = "NON_CONTROLLING_PREDECESSOR"
        elif gross_delay_days == 0:
            classification = "NO_IMPACT"
        elif float_status == "KNOWN" and net_delay_days == 0 and gross_delay_days > 0:
            classification = "ABSORBED_BY_FLOAT"
        elif execution_state == ExecutionState.IN_PROGRESS.value or execution_state == "IN_PROGRESS":
            classification = "EXECUTION_IN_PROGRESS"
        elif net_delay_days is not None and net_delay_days > 0:
            classification = "CRITICAL_PATH_SLIP"
        else:
            classification = "UNCERTAIN" if uncertainty else "NO_IMPACT"
            
    dep_type = controlling.relationship_type if controlling else (constraints[0].relationship_type if constraints else "FS")
    
    resolved_path = target_path if target_path is not None else [target_activity_id, succ_id]

    return {
        "successor_activity_id": succ_id,
        "dependency_type": dep_type,
        "original_earliest_start": baseline_start.isoformat() if baseline_start else "",
        "shifted_earliest_start": shifted_start.isoformat() if shifted_start else "",
        "propagation_depth": propagation_depth,
        "target_path": resolved_path,
        "execution_state": execution_state,
        "gross_delay_days": gross_delay_days,
        "total_float": float(raw_float) if raw_float is not None else None,
        "float_status": float_status,
        "absorbed_delay_days": absorbed_delay_days,
        "net_delay_days": net_delay_days,
        "controlling_predecessor": controlling.predecessor_activity_id if controlling else None,
        "controlling_relationship": controlling.relationship_type if controlling else None,
        "constraints_evaluated": [c.to_dict() for c in constraints],
        "uncertainty": uncertainty,
        "classification": classification,
    }


def compare_candidate_impacts(r1: Dict[str, Any], r2: Dict[str, Any]) -> int:
    """
    Deterministically compare two candidate impact evaluations for the same successor
    reached via different propagation paths or hops.
    
    Returns:
       1 if r1 is stronger / preferred over r2
      -1 if r2 is stronger / preferred over r1
       0 if equivalent
       
    Evaluation order follows canonical A1 semantics:
    1. Larger gross_delay_days (greater required schedule shift)
    2. Earlier propagation_depth (shorter causal chain / direct path preferred on ties)
    3. Lexicographical comparison of controlling_predecessor
    4. Lexicographical comparison of controlling_relationship
    """
    g1 = r1.get("gross_delay_days", 0)
    g2 = r2.get("gross_delay_days", 0)
    if g1 != g2:
        return 1 if g1 > g2 else -1

    d1 = r1.get("propagation_depth", 1)
    d2 = r2.get("propagation_depth", 1)
    if d1 != d2:
        return 1 if d1 < d2 else -1

    p1 = str(r1.get("controlling_predecessor") or "")
    p2 = str(r2.get("controlling_predecessor") or "")
    if p1 != p2:
        return 1 if p1 < p2 else -1

    rel1 = str(r1.get("controlling_relationship") or "")
    rel2 = str(r2.get("controlling_relationship") or "")
    if rel1 != rel2:
        return 1 if rel1 < rel2 else -1

    return 0

