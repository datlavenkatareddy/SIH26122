"""
PRD v6 Feature 30 -- WBS Granularity Bridge: pure decision logic.

No database or HTTP access lives here so every rule can be unit-tested
(TC-WBS-01..03). routers/matching.py loads the schedule/actuals/dependencies,
calls these functions, and persists the result to `claim_activity_splits`.

Vocabulary
----------
WBS group     A summary activity and its direct children (dotted WBS codes:
              1.02.02 -> 1.02.02.01/.02/.03), or 2+ activities sharing one
              wbs_code. Only groups with 2+ members can be decomposed.
Split         One row per sibling that receives part of a broad claim.
              `split_pct` is a FRACTION; a claim's rows sum to 1.0 +/- 0.0001.
              child contribution = claim value x split_pct (PRD M4).

Allocation rules (PRD Section 10)
---------------------------------
1. Completed sibling                      -> 0 new allocation
2. Future sibling (unstarted, planned to
   start after the claim date)            -> 0
3. Unstarted sibling behind an incomplete
   FS predecessor / unstarted SS
   predecessor inside the group           -> 0 (sequence-ineligible)
4. Quantity claim + sibling in a different
   UOM                                    -> 0 (no raw-quantity weighting across
                                             incompatible UOMs)
5. Remaining siblings share the claim, capped by their remaining headroom,
   weighted by remaining planned quantity when UOM-compatible (WBS_WEIGHTED),
   otherwise equally (EQUAL).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SUM_TOLERANCE = 0.0001
_COMPLETE_PCT = 99.999
_MIN_SHARE = 0.0001

BROAD_SCOPE_KEYWORDS = [
    "general",
    "across",
    "entire",
    "overall",
    "works in progress",
    "in progress",
    "site-wide",
    "area-wide",
    "wbs level",
    "broad claim",
    "all activities",
    "all sections",
    "all spools",
]


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _to_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val).strip()[:10])
    except (ValueError, TypeError):
        return None


def _num(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def norm_uom(uom: Any) -> Optional[str]:
    """Case/whitespace/plural-insensitive unit key ('Joints ' == 'joint')."""
    if uom is None:
        return None
    u = re.sub(r"[^a-z0-9]", "", str(uom).strip().lower())
    if not u:
        return None
    aliases = {"cum": "m3", "cubicmeter": "m3", "cubicmeters": "m3", "meter": "m", "meters": "m",
               "metre": "m", "metres": "m", "nos": "ea", "no": "ea", "each": "ea", "tons": "t",
               "ton": "t", "tonne": "t", "tonnes": "t"}
    if u in aliases:
        return aliases[u]
    if len(u) > 3 and u.endswith("s"):
        u = u[:-1]
    return u


def _wbs(act: Dict[str, Any]) -> Optional[str]:
    w = act.get("wbs_code")
    w = str(w).strip() if w is not None else ""
    return w or None


# --------------------------------------------------------------------------
# 1. WBS group discovery
# --------------------------------------------------------------------------

def find_wbs_group(
    target_activity_id: str,
    activities: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Return {"wbs_code", "kind", "summary_activity_id", "members"} for the WBS
    group the target activity belongs to, or None when it has no 2+ member
    decomposition group.

    kind = SUMMARY_CHILDREN  target is (or is a child of) a summary activity
                             whose direct children are the members
           SHARED_CODE       2+ activities share the target's exact wbs_code
    """
    by_id = {a["activity_id"]: a for a in activities}
    target = by_id.get(target_activity_id)
    if not target:
        return None
    w = _wbs(target)
    if not w:
        return None

    def direct_children(parent_code: str) -> List[Dict[str, Any]]:
        depth = parent_code.count(".") + 1
        out = [
            a for a in activities
            if (_wbs(a) or "").startswith(parent_code + ".") and (_wbs(a) or "").count(".") == depth
        ]
        return sorted(out, key=lambda a: (_wbs(a) or "", a["activity_id"]))

    # (a) target is a summary activity: its direct children
    kids = direct_children(w)
    if len(kids) >= 2:
        return {"wbs_code": w, "kind": "SUMMARY_CHILDREN",
                "summary_activity_id": target_activity_id, "members": kids}

    # (b) exact shared wbs_code
    shared = sorted([a for a in activities if _wbs(a) == w], key=lambda a: a["activity_id"])
    if len(shared) >= 2:
        return {"wbs_code": w, "kind": "SHARED_CODE", "summary_activity_id": None, "members": shared}

    # (c) target is a child of a summary activity that exists in the schedule
    if "." in w:
        parent_code = w.rsplit(".", 1)[0]
        summary = next((a for a in activities if _wbs(a) == parent_code), None)
        if summary:
            kids = direct_children(parent_code)
            if len(kids) >= 2:
                return {"wbs_code": parent_code, "kind": "SUMMARY_CHILDREN",
                        "summary_activity_id": summary["activity_id"], "members": kids}
    return None


# --------------------------------------------------------------------------
# 2. Broad vs specific claim
# --------------------------------------------------------------------------

def _distinguishing_phrases(members: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Per-member phrases that pick that member out from its siblings, e.g. for
    'Utility Header Spool Section A/B/C' -> {'...-A': ['section a']}. Built from
    the word suffix left after removing the words every sibling name shares.
    """
    token_lists = {
        m["activity_id"]: re.findall(r"[a-z0-9]+", str(m.get("activity_name") or "").lower())
        for m in members
    }
    if not token_lists:
        return {}
    common = set.intersection(*[set(t) for t in token_lists.values()]) if len(token_lists) > 1 else set()
    phrases: Dict[str, List[str]] = {}
    for aid, toks in token_lists.items():
        rest = [t for t in toks if t not in common]
        out: List[str] = []
        if rest:
            out.append(" ".join(rest))
            # keep the last shared word next to the distinguishing token: "section a"
            for i, t in enumerate(toks):
                if t in rest and i > 0 and toks[i - 1] in common:
                    out.append(f"{toks[i - 1]} {' '.join(rest)}")
                    break
        phrases[aid] = out
    return phrases


def classify_claim_scope(
    claim: Dict[str, Any],
    group: Optional[Dict[str, Any]],
    top_candidate: Optional[Dict[str, Any]] = None,
    ambiguous_within_group: bool = False,
) -> Dict[str, Any]:
    """
    Decide whether the claim is BROAD_WBS (decompose) or SPECIFIC (normal
    single-activity match). Split and normal match are mutually exclusive.
    """
    if not group or len(group.get("members", [])) < 2:
        return {"claim_scope": "SPECIFIC", "scope_reason": "Activity has no WBS group with 2+ members"}

    member_ids = {m["activity_id"] for m in group["members"]}
    summary_id = group.get("summary_activity_id")
    text = str(claim.get("raw_claim_text") or "").lower()
    reported = (claim.get("reported_activity_id") or "").strip() if claim.get("reported_activity_id") else ""
    asset = (claim.get("asset_tag") or "").strip().lower() if claim.get("asset_tag") else ""
    tier = (top_candidate or {}).get("match_tier")
    top_id = (top_candidate or {}).get("activity_id")

    # An explicit ID for a child is always specific; an ID for the summary is broad by construction.
    if reported and reported in member_ids and reported != summary_id:
        return {"claim_scope": "SPECIFIC", "scope_reason": f"Explicit child activity ID {reported}"}
    if reported and reported == summary_id:
        return {"claim_scope": "BROAD_WBS",
                "scope_reason": f"Claim references summary activity {reported} of WBS group {group['wbs_code']}"}

    # Asset tag identifying one child.
    if asset:
        for m in group["members"]:
            if str(m.get("asset_tag") or "").strip().lower() == asset:
                return {"claim_scope": "SPECIFIC", "scope_reason": f"Asset tag {asset} identifies {m['activity_id']}"}

    # Wording that names one child ("Section B").
    for aid, phrases in _distinguishing_phrases(group["members"]).items():
        for ph in phrases:
            if ph and re.search(rf"\b{re.escape(ph)}\b", text):
                return {"claim_scope": "SPECIFIC", "scope_reason": f"Claim names sub-scope '{ph}' ({aid})"}

    if tier in ("EXACT_ID", "EXACT_ASSET") and top_id in member_ids and top_id != summary_id:
        return {"claim_scope": "SPECIFIC", "scope_reason": f"{tier} match to child {top_id}"}

    hits = [kw for kw in BROAD_SCOPE_KEYWORDS if kw in text]
    if hits:
        return {"claim_scope": "BROAD_WBS",
                "scope_reason": f"Broad wording ({', '.join(repr(h) for h in hits[:2])}) across "
                                f"{len(member_ids)} activities in WBS group {group['wbs_code']}"}
    if top_id == summary_id and summary_id:
        return {"claim_scope": "BROAD_WBS",
                "scope_reason": f"Claim matches summary activity {summary_id}; no sub-scope named"}
    if ambiguous_within_group:
        return {"claim_scope": "BROAD_WBS",
                "scope_reason": f"Ambiguous between siblings of WBS group {group['wbs_code']} and no sub-scope named"}
    return {"claim_scope": "SPECIFIC", "scope_reason": "Claim describes a specific activity scope"}


# --------------------------------------------------------------------------
# 3. Allocation
# --------------------------------------------------------------------------

@dataclass
class SiblingState:
    activity_id: str
    state: str                       # COMPLETED | IN_PROGRESS | NOT_STARTED
    approved_pct: float = 0.0
    approved_qty: float = 0.0
    eligible: bool = False
    reason: str = ""
    headroom_share_cap: Optional[float] = None
    weight: float = 0.0
    notes: List[str] = field(default_factory=list)


def sibling_state(actual: Optional[Dict[str, Any]]) -> Tuple[str, float, float]:
    """(state, approved_pct, approved_qty) from an approved_actuals row (or None)."""
    if not actual:
        return "NOT_STARTED", 0.0, 0.0
    pct = _num(actual.get("actual_pct_complete")) or 0.0
    qty = _num(actual.get("actual_quantity")) or 0.0
    if actual.get("actual_finish") is not None or pct >= _COMPLETE_PCT:
        return "COMPLETED", max(pct, 100.0 if actual.get("actual_finish") is not None else pct), qty
    if actual.get("actual_start") is not None or pct > 0 or qty > 0:
        return "IN_PROGRESS", pct, qty
    return "NOT_STARTED", pct, qty


def _fix_rounding(shares: Dict[str, float]) -> Dict[str, float]:
    """Round to 4dp and push the residue into the largest share so the sum is exactly 1.0."""
    rounded = {k: round(v, 4) for k, v in shares.items()}
    rounded = {k: v for k, v in rounded.items() if v >= _MIN_SHARE}
    if not rounded:
        return {}
    diff = round(1.0 - sum(rounded.values()), 4)
    if diff:
        biggest = max(rounded, key=lambda k: (rounded[k], k))
        rounded[biggest] = round(rounded[biggest] + diff, 4)
    return rounded


def _water_fill(weights: Dict[str, float], caps: Dict[str, Optional[float]]) -> Tuple[Dict[str, float], float]:
    """
    Distribute 1.0 across ids proportionally to `weights`, never exceeding a
    member's cap (None = unbounded). Returns (shares, leftover); leftover > 0
    only when the claim exceeds the group's total remaining headroom.
    """
    shares = {k: 0.0 for k in weights}
    remaining = 1.0
    active = {k for k, w in weights.items() if w > 0}
    for _ in range(len(weights) + 1):
        if not active or remaining <= 1e-12:
            break
        total_w = sum(weights[k] for k in active)
        saturated = []
        for k in list(active):
            want = remaining * weights[k] / total_w
            cap = caps.get(k)
            room = (cap - shares[k]) if cap is not None else float("inf")
            if want >= room - 1e-12:
                shares[k] += max(room, 0.0)
                saturated.append(k)
        if not saturated:
            for k in active:
                shares[k] += remaining * weights[k] / total_w
            remaining = 0.0
            break
        remaining = 1.0 - sum(shares.values())
        active -= set(saturated)
    return shares, max(0.0, remaining)


def allocate_split(
    claim: Dict[str, Any],
    members: Sequence[Dict[str, Any]],
    actuals: Dict[str, Dict[str, Any]],
    dependencies: Iterable[Dict[str, Any]] = (),
    claim_date: Optional[Any] = None,
    summary_activity_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Allocate a broad claim across eligible sibling activities.

    claim         dict with claim_mode, claimed_pct, claimed_quantity, claimed_uom, event_date
    members       sibling activity dicts (activity_id, activity_name, planned_quantity, uom,
                  planned_start, planned_finish, wbs_code)
    actuals       {activity_id: approved_actuals row} -- current approved state
    dependencies  rows with predecessor_activity_id / successor_activity_id / relationship_type
    Returns {"status": "SUCCESS"|"FAILED", "reason", "splits": [...], "excluded": [...]}
    """
    mode = (claim.get("claim_mode") or "CUMULATIVE_PCT").upper()
    claim_pct = _num(claim.get("claimed_pct"))
    claim_qty = _num(claim.get("claimed_quantity"))
    claim_uom = norm_uom(claim.get("claimed_uom"))
    when = _to_date(claim_date) or _to_date(claim.get("event_date"))

    if mode == "INCREMENTAL_QUANTITY":
        if claim_qty is None or claim_qty <= 0:
            return {"status": "FAILED", "reason": "Incremental split requires a positive claimed_quantity",
                    "splits": [], "excluded": []}
        claim_value = claim_qty
    else:
        if claim_pct is None or claim_pct <= 0:
            return {"status": "FAILED", "reason": "Cumulative split requires a positive claimed_pct",
                    "splits": [], "excluded": []}
        claim_value = claim_pct

    ids = [m["activity_id"] for m in members]
    member_by_id = {m["activity_id"]: m for m in members}
    states: Dict[str, SiblingState] = {}
    for m in members:
        st, pct, qty = sibling_state(actuals.get(m["activity_id"]))
        states[m["activity_id"]] = SiblingState(m["activity_id"], st, pct, qty)

    # Rules 1-2, 4: completion, temporal eligibility, UOM compatibility.
    for m in members:
        s = states[m["activity_id"]]
        if s.state == "COMPLETED":
            s.reason = "already completed (0 new allocation)"
            continue
        planned_start = _to_date(m.get("planned_start"))
        if s.state == "NOT_STARTED" and when and planned_start and planned_start > when:
            s.reason = f"future activity (planned start {planned_start.isoformat()} is after claim date {when.isoformat()})"
            continue
        if mode == "INCREMENTAL_QUANTITY" and claim_uom:
            m_uom = norm_uom(m.get("uom"))
            if m_uom and m_uom != claim_uom:
                s.reason = f"UOM {m.get('uom')} incompatible with claimed UOM {claim.get('claimed_uom')}"
                continue
        s.eligible = True

    # Rule 3: sibling dependency order (only unstarted successors are gated).
    sibling_set = set(ids)
    for dep in dependencies:
        pred, succ = dep.get("predecessor_activity_id"), dep.get("successor_activity_id")
        if pred not in sibling_set or succ not in sibling_set:
            continue
        s, p = states[succ], states[pred]
        if not s.eligible or s.state != "NOT_STARTED":
            continue
        rel = (dep.get("relationship_type") or "FS").upper()
        if rel == "FS" and p.state != "COMPLETED":
            s.eligible, s.reason = False, f"waiting on predecessor {pred} (FS, not complete)"
        elif rel == "SS" and p.state == "NOT_STARTED":
            s.eligible, s.reason = False, f"waiting on predecessor {pred} (SS, not started)"

    eligible = [i for i in ids if states[i].eligible]
    excluded = [{"activity_id": i, "reason": states[i].reason or "ineligible"} for i in ids if not states[i].eligible]
    if not eligible:
        why = "; ".join(f"{e['activity_id']}: {e['reason']}" for e in excluded) or "no siblings"
        return {"status": "FAILED", "reason": f"No eligible sibling activity to receive the claim ({why})",
                "splits": [], "excluded": excluded}

    # Weights and headroom caps.
    uoms = {norm_uom(member_by_id[i].get("uom")) for i in eligible}
    quantity_weightable = (
        len(uoms) == 1 and None not in uoms
        and (mode == "CUMULATIVE_PCT" or (claim_uom is not None and uoms == {claim_uom}))
        and all((_num(member_by_id[i].get("planned_quantity")) or 0) > 0 for i in eligible)
    )
    weights: Dict[str, float] = {}
    caps: Dict[str, Optional[float]] = {}
    for i in eligible:
        s, m = states[i], member_by_id[i]
        planned = _num(m.get("planned_quantity")) or 0.0
        if mode == "CUMULATIVE_PCT":
            room = max(0.0, 100.0 - s.approved_pct)
            caps[i] = room / claim_value if claim_value else None
            remaining_fraction = room / 100.0
            weights[i] = (planned * remaining_fraction) if quantity_weightable else max(remaining_fraction, 1e-9)
        else:
            if planned > 0 and quantity_weightable:
                room_q = max(0.0, planned - s.approved_qty)
                caps[i] = room_q / claim_value
                weights[i] = room_q
            else:
                caps[i], weights[i] = None, 1.0
        if weights[i] <= 0:
            weights[i] = 0.0
            s.notes.append("no remaining headroom")
    if sum(weights.values()) <= 0:
        return {"status": "FAILED", "reason": "Eligible siblings have no remaining headroom",
                "splits": [], "excluded": excluded}

    shares, leftover = _water_fill(weights, caps)
    overflow_note = ""
    if leftover > 1e-9:
        # Claim exceeds the group's remaining headroom: keep the sum at 1.0 and let
        # M4's physical validation flag the resulting over-100 / over-plan child.
        total_w = sum(weights[i] for i in eligible if weights[i] > 0)
        for i in eligible:
            if weights[i] > 0:
                shares[i] += leftover * weights[i] / total_w
        overflow_note = " Claim exceeds remaining headroom; excess left for physical validation."

    final = _fix_rounding({i: shares[i] for i in eligible})
    if not final:
        return {"status": "FAILED", "reason": "Allocation produced no positive share", "splits": [],
                "excluded": excluded}

    basis = "WBS_WEIGHTED" if quantity_weightable else "EQUAL"
    rows: List[Dict[str, Any]] = []
    for i in ids:
        if i not in final:
            continue
        m, s = member_by_id[i], states[i]
        share = final[i]
        contribution = round(claim_value * share, 4)
        rows.append({
            "activity_id": i,
            "wbs_code": _wbs(m),
            "split_basis": basis,
            "split_pct": share,
            "planned_quantity": _num(m.get("planned_quantity")),
            "uom": m.get("uom"),
            "allocated_quantity": contribution if mode == "INCREMENTAL_QUANTITY" else None,
            "allocated_pct": contribution if mode == "CUMULATIVE_PCT" else None,
            "rationale": (
                f"{s.state.replace('_', ' ').lower()} sibling"
                + (f", approved {s.approved_pct:g}%" if s.approved_pct else "")
                + f"; {basis.replace('_', '-').lower()} share {share:.4f}"
            ),
        })
    return {
        "status": "SUCCESS",
        "reason": (f"Allocated {claim_value:g} across {len(rows)} of {len(ids)} WBS siblings "
                   f"({basis}).{overflow_note}"),
        "splits": rows,
        "excluded": excluded,
    }


# --------------------------------------------------------------------------
# 4. Supervisor manual edit
# --------------------------------------------------------------------------

class SplitEditError(ValueError):
    pass


def apply_manual_split_edit(
    existing: Sequence[Dict[str, Any]],
    edits: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Apply a Supervisor edit of split_pct values. `edits` is
    [{"activity_id", "split_pct"}]. Rows omitted from the edit or set to 0 are dropped.
    Touched rows whose value changed become MANUAL. The result must sum to
    1.0 +/- 0.0001 (never auto-repaired). Raises SplitEditError on invalid input.
    """
    by_id = {r["activity_id"]: dict(r) for r in existing}
    if not by_id:
        raise SplitEditError("No persisted splits exist for this claim")
    out: Dict[str, Dict[str, Any]] = {}
    for e in edits:
        aid = e.get("activity_id")
        if aid not in by_id:
            raise SplitEditError(f"Activity '{aid}' is not part of this claim's WBS split")
        if aid in out:
            raise SplitEditError(f"Duplicate activity '{aid}' in edit")
        pct = _num(e.get("split_pct"))
        if pct is None or pct < 0:
            raise SplitEditError(f"Invalid split_pct for '{aid}'")
        if pct == 0:
            continue
        row = by_id[aid]
        if abs(round(pct, 4) - round(float(row["split_pct"]), 4)) > 1e-9:
            row["split_basis"] = "MANUAL"
        row["split_pct"] = round(pct, 4)
        out[aid] = row
    if not out:
        raise SplitEditError("At least one activity must keep a positive split_pct")
    total = round(sum(r["split_pct"] for r in out.values()), 4)
    if abs(total - 1.0) > SUM_TOLERANCE:
        raise SplitEditError(f"split_pct values sum to {total}, expected 1.0000 +/- {SUM_TOLERANCE}")
    return sorted(out.values(), key=lambda r: r["activity_id"])
