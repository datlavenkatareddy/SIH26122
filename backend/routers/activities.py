import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.shared.auth import UserProfile, require_role
from backend.shared.db import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])


def fetch_activity_metadata(
    activity_id: str,
    conn: Optional[Any] = None,
) -> Optional[dict]:
    """
    Retrieve authoritative schedule activity metadata joined with approved_actuals.
    """
    query = """
        SELECT
            sa.activity_id,
            sa.schedule_id,
            sa.activity_name,
            sa.wbs_code,
            sa.discipline,
            sa.location,
            sa.asset_tag,
            sa.planned_start,
            sa.planned_finish,
            sa.planned_quantity,
            sa.uom,
            sa.baseline_pct_complete,
            aa.actual_pct_complete AS approved_pct,
            aa.actual_quantity AS approved_quantity,
            aa.actual_start,
            aa.actual_finish,
            aa.decision_id
        FROM schedule_activities sa
        LEFT JOIN approved_actuals aa
            ON aa.schedule_id = sa.schedule_id AND aa.activity_id = sa.activity_id
        WHERE sa.activity_id = %s
        ORDER BY sa.planned_start ASC
        LIMIT 1
    """
    try:
        if conn is not None:
            row = conn.execute(query, (activity_id,)).fetchone()
        else:
            with get_connection() as c:
                row = c.execute(query, (activity_id,)).fetchone()

        if not row:
            return None

        approved_pct = float(row["approved_pct"]) if row["approved_pct"] is not None else 0.0
        if approved_pct >= 100.0:
            status_val = "COMPLETED"
        elif approved_pct > 0.0:
            status_val = "IN PROGRESS"
        else:
            status_val = "NOT STARTED"

        return {
            "activity_id": str(row["activity_id"]),
            "schedule_id": str(row["schedule_id"]),
            "activity_name": str(row["activity_name"]),
            "wbs_code": str(row["wbs_code"]) if row["wbs_code"] else None,
            "discipline": str(row["discipline"]),
            "location": str(row["location"]),
            "asset_tag": str(row["asset_tag"]) if row["asset_tag"] else None,
            "planned_start": str(row["planned_start"]),
            "planned_finish": str(row["planned_finish"]),
            "planned_quantity": float(row["planned_quantity"]) if row["planned_quantity"] is not None else None,
            "uom": str(row["uom"]) if row["uom"] else None,
            "baseline_pct_complete": float(row["baseline_pct_complete"]) if row["baseline_pct_complete"] is not None else 0.0,
            "approved_pct": approved_pct,
            "approved_quantity": float(row["approved_quantity"]) if row["approved_quantity"] is not None else None,
            "actual_start": str(row["actual_start"]) if row["actual_start"] else None,
            "actual_finish": str(row["actual_finish"]) if row["actual_finish"] else None,
            "status": status_val,
        }
    except Exception as e:
        logger.debug("Failed to fetch activity metadata for %s: %s", activity_id, e)
        return None


def query_activity_history(
    activity_id: str,
    conn: Optional[Any] = None,
) -> dict:
    """
    Retrieve chronological activity history timeline for an activity.

    Core business rules:
    1. For the specified activity_id, retrieve all linked execution_events:
       - Where the event's latest planner_decision has selected_activity_id = activity_id, OR
       - Where no planner_decision exists, but matched_activity_id or reported_activity_id = activity_id.
    2. For every linked execution_event, retrieve all linked source_references and planner_decisions.
    3. Retrieve the single final planner_decision for the activity:
       - Ordered by decided_at DESC, decision_id DESC LIMIT 1.
    4. Assemble a unified timeline ordered chronologically:
       - timestamp ASC
       - type == "execution_event" before "planner_decision"
       - event_id / decision_id deterministic tie-breaker.
    5. Return {"activity_id": activity_id, "timeline": [...]}.
    """
    events_query = """
        SELECT
            ee.event_id,
            ee.document_id,
            ee.schedule_id,
            ee.event_date,
            ee.raw_claim_text,
            ee.input_channel,
            ee.language_detected,
            ee.reported_activity_id,
            ee.matched_activity_id,
            ee.discipline,
            ee.action,
            ee.event_type,
            ee.claim_mode,
            ee.asset_tag,
            ee.location,
            ee.claimed_quantity,
            ee.claimed_uom,
            ee.claimed_pct,
            ee.delay_reason,
            ee.supervisor_id,
            ee.photo_path,
            ee.status,
            ee.created_at
        FROM execution_events ee
        WHERE (
            ee.event_id IN (
                SELECT pd.event_id
                FROM planner_decisions pd
                WHERE pd.selected_activity_id = %s
                  AND pd.decision_id = (
                      SELECT pd2.decision_id
                      FROM planner_decisions pd2
                      WHERE pd2.event_id = pd.event_id
                      ORDER BY pd2.decided_at DESC, pd2.decision_id DESC
                      LIMIT 1
                  )
            )
            OR (
                NOT EXISTS (
                    SELECT 1 FROM planner_decisions pd3 WHERE pd3.event_id = ee.event_id
                )
                AND (ee.matched_activity_id = %s OR ee.reported_activity_id = %s)
            )
        )
        ORDER BY ee.event_date ASC, ee.created_at ASC, ee.event_id ASC
    """

    decision_query = """
        SELECT
            decision_id,
            event_id,
            selected_activity_id,
            action,
            approved_pct,
            approved_qty,
            planner_id,
            justification,
            decided_at
        FROM planner_decisions
        WHERE selected_activity_id = %s
        ORDER BY decided_at DESC, decision_id DESC
        LIMIT 1
    """

    if conn is not None:
        event_rows = conn.execute(events_query, (activity_id, activity_id, activity_id)).fetchall()
        decision_row = conn.execute(decision_query, (activity_id,)).fetchone()
    else:
        with get_connection() as c:
            event_rows = c.execute(events_query, (activity_id, activity_id, activity_id)).fetchall()
            decision_row = c.execute(decision_query, (activity_id,)).fetchone()

    event_ids = [str(r["event_id"]) for r in event_rows]

    refs_by_event: Dict[str, List[dict]] = {}
    decisions_by_event: Dict[str, dict] = {}

    if event_ids:
        placeholders = ", ".join(["%s"] * len(event_ids))
        refs_query = f"""
            SELECT
                reference_id,
                event_id,
                file_name,
                sheet_name,
                row_cell_ref,
                message_id,
                raw_snippet
            FROM source_references
            WHERE event_id IN ({placeholders})
            ORDER BY reference_id ASC
        """
        dec_all_query = f"""
            SELECT
                decision_id,
                event_id,
                selected_activity_id,
                action,
                approved_pct,
                approved_qty,
                planner_id,
                justification,
                decided_at
            FROM planner_decisions
            WHERE event_id IN ({placeholders})
            ORDER BY decided_at ASC, decision_id ASC
        """
        if conn is not None:
            ref_rows = conn.execute(refs_query, tuple(event_ids)).fetchall()
            dec_rows = conn.execute(dec_all_query, tuple(event_ids)).fetchall()
        else:
            with get_connection() as c:
                ref_rows = c.execute(refs_query, tuple(event_ids)).fetchall()
                dec_rows = c.execute(dec_all_query, tuple(event_ids)).fetchall()

        for ref in ref_rows:
            e_id = str(ref["event_id"])
            if e_id not in refs_by_event:
                refs_by_event[e_id] = []
            refs_by_event[e_id].append(
                {
                    "reference_id": str(ref["reference_id"]),
                    "file_name": ref["file_name"] if ref["file_name"] is not None else None,
                    "sheet_name": ref["sheet_name"] if ref["sheet_name"] is not None else None,
                    "row_cell_ref": ref["row_cell_ref"] if ref["row_cell_ref"] is not None else None,
                    "message_id": ref["message_id"] if ref["message_id"] is not None else None,
                    "raw_snippet": str(ref["raw_snippet"] or ""),
                }
            )

        for d in dec_rows:
            decisions_by_event[str(d["event_id"])] = d

    timeline: List[dict] = []

    for event in event_rows:
        ts = None
        if event["created_at"] is not None:
            ts = str(event["created_at"])
        elif event["event_date"] is not None:
            ts = str(event["event_date"])

        e_id = str(event["event_id"])
        dec = decisions_by_event.get(e_id)

        timeline.append(
            {
                "type": "execution_event",
                "event_id": e_id,
                "schedule_id": str(event["schedule_id"]) if event["schedule_id"] is not None else None,
                "event_date": str(event["event_date"]) if event["event_date"] is not None else None,
                "raw_claim_text": str(event["raw_claim_text"] or ""),
                "claim_mode": str(event["claim_mode"]) if event["claim_mode"] is not None else "CUMULATIVE_PCT",
                "claimed_pct": float(event["claimed_pct"]) if event["claimed_pct"] is not None else None,
                "claimed_quantity": float(event["claimed_quantity"]) if event["claimed_quantity"] is not None else None,
                "claimed_uom": str(event["claimed_uom"]) if event["claimed_uom"] is not None else None,
                "input_channel": str(event["input_channel"] or ""),
                "reported_activity_id": str(event["reported_activity_id"]) if event["reported_activity_id"] is not None else None,
                "matched_activity_id": str(event["matched_activity_id"]) if event["matched_activity_id"] is not None else None,
                "discipline": str(event["discipline"]) if event["discipline"] is not None else None,
                "location": str(event["location"]) if event["location"] is not None else None,
                "asset_tag": str(event["asset_tag"]) if event["asset_tag"] is not None else None,
                "delay_reason": str(event["delay_reason"]) if event["delay_reason"] is not None else None,
                "status": str(event["status"]) if event["status"] is not None else None,
                "timestamp": ts,
                "source_references": refs_by_event.get(e_id, []),
                "supervisor_action": str(dec["action"]) if dec else None,
                "approved_pct": float(dec["approved_pct"]) if dec and dec["approved_pct"] is not None else None,
                "approved_qty": float(dec["approved_qty"]) if dec and dec["approved_qty"] is not None else None,
                "justification": str(dec["justification"]) if dec and dec["justification"] else None,
                "decision": {
                    "decision_id": str(dec["decision_id"]),
                    "action": str(dec["action"]),
                    "approved_pct": float(dec["approved_pct"]) if dec["approved_pct"] is not None else None,
                    "approved_qty": float(dec["approved_qty"]) if dec["approved_qty"] is not None else None,
                    "planner_id": str(dec["planner_id"]),
                    "justification": str(dec["justification"] or ""),
                    "decided_at": str(dec["decided_at"]) if dec["decided_at"] is not None else None,
                } if dec else None,
            }
        )

    if decision_row:
        dec_ts = str(decision_row["decided_at"]) if decision_row["decided_at"] is not None else None
        timeline.append(
            {
                "type": "planner_decision",
                "decision_id": str(decision_row["decision_id"]),
                "event_id": str(decision_row["event_id"]),
                "selected_activity_id": str(decision_row["selected_activity_id"]),
                "action": str(decision_row["action"]),
                "approved_pct": float(decision_row["approved_pct"]) if decision_row["approved_pct"] is not None else None,
                "approved_qty": float(decision_row["approved_qty"]) if decision_row["approved_qty"] is not None else None,
                "justification": str(decision_row["justification"]) if decision_row["justification"] is not None else "",
                "timestamp": dec_ts,
            }
        )

    timeline.sort(
        key=lambda item: (
            str(item.get("timestamp") or ""),
            0 if item.get("type") == "execution_event" else 1,
            str(item.get("event_id") if item.get("type") == "execution_event" else item.get("decision_id")),
        )
    )

    return {
        "activity_id": str(activity_id),
        "timeline": timeline,
    }


@router.get("")
def list_activities(
    schedule_id: Optional[str] = Query(None),
    discipline: Optional[str] = Query(None),
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    List schedule activities joined with authoritative approved actuals.
    Restricted to SUPERVISOR role.
    """
    try:
        with get_connection() as conn:
            active_sched_id = schedule_id
            if not active_sched_id:
                sched_row = conn.execute(
                    "SELECT schedule_id FROM schedules ORDER BY created_at DESC LIMIT 1"
                ).fetchone()
                if sched_row:
                    active_sched_id = str(sched_row["schedule_id"])
                else:
                    act_sched = conn.execute(
                        "SELECT schedule_id FROM schedule_activities LIMIT 1"
                    ).fetchone()
                    if act_sched:
                        active_sched_id = str(act_sched["schedule_id"])

            schedules_rows = conn.execute(
                "SELECT schedule_id, project_name, data_date, source_format FROM schedules ORDER BY created_at DESC"
            ).fetchall()
            schedules_list = [
                {
                    "schedule_id": str(s["schedule_id"]),
                    "project_name": str(s["project_name"]),
                    "data_date": str(s["data_date"]) if s["data_date"] else None,
                    "source_format": str(s["source_format"]) if s["source_format"] else None,
                }
                for s in schedules_rows
            ]

            if not active_sched_id:
                return {
                    "schedule_id": None,
                    "schedules": schedules_list,
                    "activities": [],
                }

            if discipline:
                query = """
                    SELECT
                        sa.activity_id,
                        sa.schedule_id,
                        sa.activity_name,
                        sa.wbs_code,
                        sa.discipline,
                        sa.location,
                        sa.asset_tag,
                        sa.planned_start,
                        sa.planned_finish,
                        sa.planned_quantity,
                        sa.uom,
                        sa.baseline_pct_complete,
                        aa.actual_pct_complete AS approved_pct,
                        aa.actual_quantity AS approved_quantity,
                        aa.actual_start,
                        aa.actual_finish,
                        aa.decision_id
                    FROM schedule_activities sa
                    LEFT JOIN approved_actuals aa
                        ON aa.schedule_id = sa.schedule_id AND aa.activity_id = sa.activity_id
                    WHERE sa.schedule_id = %s AND sa.discipline = %s
                    ORDER BY sa.activity_id ASC
                """
                rows = conn.execute(query, (active_sched_id, discipline)).fetchall()
            else:
                query = """
                    SELECT
                        sa.activity_id,
                        sa.schedule_id,
                        sa.activity_name,
                        sa.wbs_code,
                        sa.discipline,
                        sa.location,
                        sa.asset_tag,
                        sa.planned_start,
                        sa.planned_finish,
                        sa.planned_quantity,
                        sa.uom,
                        sa.baseline_pct_complete,
                        aa.actual_pct_complete AS approved_pct,
                        aa.actual_quantity AS approved_quantity,
                        aa.actual_start,
                        aa.actual_finish,
                        aa.decision_id
                    FROM schedule_activities sa
                    LEFT JOIN approved_actuals aa
                        ON aa.schedule_id = sa.schedule_id AND aa.activity_id = sa.activity_id
                    WHERE sa.schedule_id = %s
                    ORDER BY sa.activity_id ASC
                """
                rows = conn.execute(query, (active_sched_id,)).fetchall()

            activities = []
            for r in rows:
                approved_pct = float(r["approved_pct"]) if r["approved_pct"] is not None else 0.0
                if approved_pct >= 100.0:
                    status_val = "COMPLETED"
                elif approved_pct > 0.0:
                    status_val = "IN PROGRESS"
                else:
                    status_val = "NOT STARTED"

                activities.append({
                    "activity_id": str(r["activity_id"]),
                    "schedule_id": str(r["schedule_id"]),
                    "activity_name": str(r["activity_name"]),
                    "wbs_code": str(r["wbs_code"]) if r["wbs_code"] else None,
                    "discipline": str(r["discipline"]),
                    "location": str(r["location"]),
                    "asset_tag": str(r["asset_tag"]) if r["asset_tag"] else None,
                    "planned_start": str(r["planned_start"]),
                    "planned_finish": str(r["planned_finish"]),
                    "planned_quantity": float(r["planned_quantity"]) if r["planned_quantity"] is not None else None,
                    "uom": str(r["uom"]) if r["uom"] else None,
                    "baseline_pct_complete": float(r["baseline_pct_complete"]) if r["baseline_pct_complete"] is not None else 0.0,
                    "approved_pct": approved_pct,
                    "approved_quantity": float(r["approved_quantity"]) if r["approved_quantity"] is not None else None,
                    "actual_start": str(r["actual_start"]) if r["actual_start"] else None,
                    "actual_finish": str(r["actual_finish"]) if r["actual_finish"] else None,
                    "status": status_val,
                })

            return {
                "schedule_id": active_sched_id,
                "schedules": schedules_list,
                "activities": activities,
            }
    except Exception as e:
        logger.error("Failed to list activities: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list activities: {str(e)}",
        )


@router.get("/{activity_id}/history")
def get_activity_history(
    activity_id: str,
    current_user: UserProfile = Depends(require_role("SUPERVISOR")),
):
    """
    Chronological activity history timeline for an activity.
    Combines linked execution_events, their source_references, and the final planner_decision.
    Restricted to SUPERVISOR role.
    """
    try:
        data = query_activity_history(activity_id=activity_id)
        # Augment with authoritative schedule activity metadata if available
        meta = fetch_activity_metadata(activity_id)
        if meta:
            data["activity"] = meta
        return data
    except Exception as e:
        logger.error("Failed to query activity history for '%s': %s", activity_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve activity history for '{activity_id}'",
        )

