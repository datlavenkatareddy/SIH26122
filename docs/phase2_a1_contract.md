# Phase 2 A1 — Schedule Impact Preview Contract (Half 1)

## 1. Current Behavior
- **Endpoint**: `GET /api/v1/schedule/{activity_id}/impact-preview?delay_days=N` (restricted to `SUPERVISOR`).
- **Traversal**: Exactly 1 level downstream direct successors.
- **Relationship Type**: Hardcoded to `UPPER(TRIM(sd.relationship_type)) = 'FS'`. All `SS`, `FF`, `SF` relationships are discarded.
- **Delay Formula**: `shifted_earliest_start = successor.planned_start + delay_days`. Blindly shifts start date without regard to predecessor finish date or successor duration.
- **Lag/Lead**: `lag_days` ignored entirely.
- **Float**: `total_float` ignored. No distinction between zero float and unknown (`NULL`) float.
- **Execution State**: Ignored. Completed activities are shifted as if not started.
- **Multi-Predecessor Control**: Ignored. The target activity is blindly assumed to be the sole controlling driver.

## 2. Current Gaps
1. **Relationship Blindness**: Ignores `SS`, `FF`, `SF`, preventing real-world EPC/Primavera precedence modeling.
2. **Missing Predecessor Reconciliation**: Successors with multiple predecessors are not reconciled to find the true controlling path.
3. **No Float Absorption**: Zero float vs missing float is unhandled; float absorption is completely absent.
4. **Execution State Disregard**: Completed or in-progress tasks are treated identically to unstarted tasks.
5. **No Lag/Lead Support**: Delays or leads on dependencies are ignored.

## 3. Frozen A1 Calculation Contract

### 3.1 Cross-Dimension Constraint Reconciliation
All predecessor constraints are projected onto a single unified comparison dimension: **`REQUIRED SUCCESSOR START`**.
- **FS**: $\text{required\_start} = \text{predecessor.simulated\_finish} + \text{lag}$
- **SS**: $\text{required\_start} = \text{predecessor.simulated\_start} + \text{lag}$
- **FF**: 
  - $\text{required\_finish} = \text{predecessor.simulated\_finish} + \text{lag}$
  - $\text{required\_start} = \text{required\_finish} - \text{successor.planned\_duration}$
- **SF**:
  - $\text{required\_finish} = \text{predecessor.simulated\_start} + \text{lag}$
  - $\text{required\_start} = \text{required\_finish} - \text{successor.planned\_duration}$

*Uncertainty Guard*: If successor duration cannot be determined (missing `planned_start` or `planned_finish`), do NOT fabricate duration. Return `uncertainty = True` with an explicit reason.

### 3.2 Controlling Constraint & Deterministic Tie-Break
The controlling constraint is the one demanding the latest `required_successor_start`.
If tied:
1. Larger `gross_delay_days`
2. Lexicographically earlier `predecessor_activity_id` (ASC)
3. Lexicographically earlier `relationship_type` (ASC)

### 3.3 Float Contract
- If `total_float IS NULL`:
  - `float_status = "UNKNOWN"`
  - `absorbed_delay_days = null`
  - `net_delay_days = null`
  - `uncertainty = True`
  - `gross_delay_days` remains exposed so movement is visible.
- If `total_float IS NOT NULL`:
  - `float_status = "KNOWN"`
  - $\text{absorbed\_delay\_days} = \min(\max(\text{gross\_delay\_days}, 0), \max(\text{total\_float}, 0))$
  - $\text{net\_delay\_days} = \max(\text{gross\_delay\_days} - \max(\text{total\_float}, 0), 0)$

### 3.4 Execution State Semantics
Uses Phase 1 canonical `get_execution_state()`:
- **COMPLETED successor**: If the activity being evaluated as the affected successor is already `COMPLETED`, its calculated impact is 0 and it must not be shifted (`gross_delay = 0, net_delay = 0`).
- **NOT_STARTED / IN_PROGRESS successor**: Evaluate normally according to the frozen constraint contract. For `IN_PROGRESS`, preserve standard planned duration propagation and mark `IN_PROGRESS` without speculative ML remaining duration.
- **Target Activity Independence**: Do NOT use the target activity's execution state as a blanket reason to skip successor evaluation. Even if Target A is `COMPLETED`, hypothetical delay simulated on A must propagate to evaluate downstream uncompleted successors normally.

### 3.5 Traversal & Query Strategy
- Frontier-batched traversal up to `MAX_IMPACT_HOPS = 3`.
- Per-frontier batched query for outgoing dependencies, incoming dependencies of discovered successors, activity metadata, and approved actuals (strictly avoids N+1 queries).

### 3.6 Predecessor Simulated Date Shift Contract (Multi-Hop Propagation)
- For a predecessor participating in a downstream propagation step, its relevant constraint dates are its baseline planned dates shifted by its currently selected propagated net delay:
  - $\text{predecessor.simulated\_start} = \text{predecessor.planned\_start} + \text{timedelta}(\text{days}=\text{propagated\_net\_delay})$
  - $\text{predecessor.simulated\_finish} = \text{predecessor.planned\_finish} + \text{timedelta}(\text{days}=\text{propagated\_net\_delay})$
- For the initial disturbance (target activity), `propagated_net_delay = hypothetical_delay_days`.
- For unimpacted predecessors, `propagated_net_delay = 0`.

### 3.7 Float-Aware Delay Propagation & NULL Float Halt
- Only activities with `float_status == "KNOWN"` and $\text{net\_delay\_days} > 0$ propagate downstream schedule delay.
- If $\text{net\_delay\_days} \le 0$ (e.g. absorbed completely by float), propagation ceases on that branch.
- If $\text{total\_float IS NULL}$ (`float_status == "UNKNOWN"`): $\text{net\_delay\_days} = \text{null}$. No numeric delay is fabricated or propagated downstream. The branch halts with `uncertainty = True`.

### 3.8 Cycle Protection
- A `visited` set tracks processed activities and their earliest propagation depth.
- If a cycle is detected ($A \rightarrow B \rightarrow C \rightarrow A$), previously visited activities are not re-enqueued, guaranteeing finite termination.

### 3.9 Converging Paths & Deterministic Resolution
- When an activity is reachable through multiple paths (e.g. $A \rightarrow B \rightarrow D$ and $A \rightarrow C \rightarrow D$), it appears exactly once in the final impacts list.
- Resolution occurs through **full A1 constraint evaluation**: all incoming constraints from all active predecessors are evaluated simultaneously against their respective simulated dates. The controlling constraint is chosen using the 4-tier tie-break comparator, and the resulting gross delay, float absorption, and net delay govern.

### 3.10 Structured Reasoning & Backward Compatibility
- Each impact item includes:
  - `successor_activity_id`, `dependency_type`, `original_earliest_start`, `shifted_earliest_start` (backward-compatible)
  - `propagation_depth`: integer hop distance from target (1, 2, 3)
  - `target_path`: list of activity IDs from target to successor (e.g. `['A', 'B', 'D']`)
  - `execution_state`, `gross_delay_days`, `total_float`, `float_status`, `absorbed_delay_days`, `net_delay_days`, `controlling_predecessor`, `controlling_relationship`, `constraints_evaluated`, `uncertainty`, `classification`
- Top-level response preserves `activity_id`, `delay_days`, `impacts`, and includes `propagation_depth_limit = 3`.

## 4. Test Cases (Half 1)
- `IMP-01`: FS relationship constraint propagation
- `IMP-02`: SS relationship constraint propagation
- `IMP-03`: FF relationship constraint conversion via successor duration
- `IMP-04`: SF relationship constraint conversion via successor duration
- `IMP-05`: Positive lag adds delay to constraint boundary
- `IMP-06`: Negative lead advances constraint boundary
- `IMP-07`: Mixed FS + FF predecessor reconciliation on unified start dimension
- `IMP-08`: Non-target predecessor controlling selection
- `IMP-09`: Deterministic tie-break resolution
- `IMP-10`: Known float absorbs delay completely ($\text{net\_delay} = 0$)
- `IMP-11`: Gross delay exceeds float ($\text{net\_delay} > 0$)
- `IMP-12`: `NULL` float produces `UNKNOWN` status, `null` net delay (no implicit zero)
- `IMP-13`: `NOT_STARTED` execution state handling
- `IMP-14`: `IN_PROGRESS` execution state handling
- `IMP-15`: `COMPLETED` execution state does not shift
- `IMP-16`: Missing successor duration produces explicit uncertainty
- `IMP-17`: Batched database query verification (no N+1)

## 5. Test Cases (Half 2: Propagation)
- `PROP-01`: 2-hop propagation ($A \rightarrow B \rightarrow C$)
- `PROP-02`: 3-hop propagation ($A \rightarrow B \rightarrow C \rightarrow D$)
- `PROP-03`: Bounded stop at `MAX_IMPACT_HOPS = 3`
- `PROP-04`: Cycle protection ($A \rightarrow B \rightarrow C \rightarrow A$)
- `PROP-05`: Completed successor does not shift (impact = 0)
- `PROP-06`: Completed successor does not propagate delay downstream
- `PROP-07`: In-progress successor uses planned duration semantics
- `PROP-08`: NOT_STARTED successor propagates normally
- `PROP-09`: Float absorption reduces propagated delay ($A \text{ delay}=5, B \text{ float}=3 \implies C \text{ receives } 2$)
- `PROP-10`: NULL float does not become zero during propagation
- `PROP-11`: NULL float produces null net delay and halts numeric delay propagation
- `PROP-12`: Multiple paths converge on same successor without duplicate output
- `PROP-13`: Multiple predecessors reconciled at downstream hop
- `PROP-14`: Non-target predecessor controlling downstream
- `PROP-15`: Mixed relationship types across hops (FS $\rightarrow$ SS $\rightarrow$ FF)
- `PROP-16`: Positive lag & negative lead across hops
- `PROP-17`: Database immutability (schedule dates unchanged after preview)
- `PROP-18`: Batched query execution verification (zero N+1 queries)
- `PROP-19`: Structured path / explanation trace returned
- `PROP-20`: Backward compatibility of legacy response fields
