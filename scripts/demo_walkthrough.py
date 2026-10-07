"""
Scripted PRD Section 26 walkthrough against a running backend (creates its own demo claims;
never bulk-approves anything else):

  Site Engineer: submit a broad claim -> (answer the clarification if asked) -> match -> check
  Supervisor:    priority queue -> edit the WBS split -> approve/edit with justification
  Outputs:       approved actuals + rollup, audit chain validity, CSV, P6 mock write-back,
                 knowledge graph + Ask Why, execution summary

    python scripts/demo_walkthrough.py
"""
from _demo_client import call

TEXT = "Utility header fabrication progressing, 12 m completed across the header sections at Pump Station 3"


def step(title):
    print(f"\n=== {title}")


def submit_claim():
    s, b = call("SITE_ENGINEER", "POST", "/api/v1/claims/text", json={"raw_claim_text": TEXT})
    assert s == 200, b
    eid = b["event_id"]
    print(f"extracted: mode={b['claim_mode']} qty={b['claimed_quantity']} {b['claimed_uom']} "
          f"discipline={b['discipline']} lang={b['language_detected']} clarification={b['clarification_status']}")
    if b["clarification_status"] == "PENDING":
        print("clarification question:", b["clarification_question"])
        s, b = call("SITE_ENGINEER", "POST", f"/api/v1/claims/{eid}/clarify",
                    json={"answer": "Piping progress update: 12 m of header fabricated today (incremental quantity in metres)"})
        print("after answer:", b["clarification_status"], b["claim_mode"], b["claimed_quantity"], b["claimed_uom"])
    s, m = call("SITE_ENGINEER", "POST", f"/api/v1/claims/{eid}/match")
    print(f"match: {m['status']} scope={m['claim_scope']} matched={m['matched_activity_id']} -> {m['allocation_reason']}")
    for x in m["excluded_siblings"]:
        print(f"   excluded {x['activity_id']}: {x['reason']}")
    s, c = call("SITE_ENGINEER", "POST", f"/api/v1/claims/{eid}/check")
    print(f"check: {c['status']} issues={[i['rule_code'] for i in c['validation_issues']]} priority={c['priority_score']}")
    return eid, m


step("P6 mock before")
_, before = call("SUPERVISOR", "GET", "/api/v1/mock-p6/received")
step("1) Site Engineer submits a broad claim")
eid, m = submit_claim()

step("2) Supervisor: priority-sorted review queue")
_, q = call("SUPERVISOR", "GET", "/api/v1/review-queue?sort=priority")
for it in q["items"][:5]:
    print(f"   {it['priority_score']:>7}  {it['status']:<16} {it['event_id'][:8]}  {it['raw_claim_text'][:60]}")

step("3) Supervisor: WBS split (edit shares)")
_, sp = call("SUPERVISOR", "GET", f"/api/v1/claims/{eid}/splits")
rows = sp["splits"]
print("suggested:", [(r["activity_id"], r["split_pct"], r["split_basis"]) for r in rows])
if len(rows) >= 2:
    a, b = rows[0]["activity_id"], rows[1]["activity_id"]
    s, p = call("SUPERVISOR", "PATCH", f"/api/v1/claims/{eid}/splits",
                json={"splits": [{"activity_id": a, "split_pct": 0.6}, {"activity_id": b, "split_pct": 0.4}]})
    print("edited:", [(r["activity_id"], r["split_pct"], r["split_basis"]) for r in p["splits"]] if s == 200 else p)
    call("SITE_ENGINEER", "POST", f"/api/v1/claims/{eid}/check")

step("4) Ask Why + knowledge graph")
focus = rows[0]["activity_id"] if rows else m["candidates"][0]["activity_id"]
_, w = call("SUPERVISOR", "GET", f"/api/v1/graph/explain/{focus}?event_id={eid}&depth=2")
print("\n".join("  - " + x for x in w["reasoning_steps"]))
_, g = call("SUPERVISOR", "GET", f"/api/v1/claims/{eid}/knowledge-graph")
print(f"graph: {len(g['nodes'])} nodes, {len(g['edges'])} edges, types={sorted({n['type'] for n in g['nodes']})}")

step("5) Supervisor approves with justification")
s, d = call("SUPERVISOR", "POST", "/api/v1/decisions",
            json={"event_id": eid, "action": "APPROVE", "justification": "Verified against site diary (demo walkthrough)"})
print(s, [(x["activity_id"], x["actual_quantity"]) for x in d.get("approved_actuals", [])] or d)

step("6) Audit chain, P6 mock write-back, CSV")
_, au = call("SUPERVISOR", "GET", f"/api/v1/audit/{eid}")
print("audit entries:", len(au["logs"]), "| chain_valid:", au["chain_valid"])
_, after = call("SUPERVISOR", "GET", "/api/v1/mock-p6/received")
print("P6 mock payloads added:", after["count"] - before["count"], after["payloads"][-2:])
s, csv_body = call("SUPERVISOR", "GET", "/api/v1/export/csv")
print("CSV:", str(csv_body).splitlines()[0] if s == 200 else s)

step("7) Live dashboard + execution summary")
_, dash = call("SUPERVISOR", "GET", "/api/v1/dashboard/summary")
print({k: dash[k] for k in ("total_claims", "pending_review", "actuals", "conflicts")})
_, rep = call("SUPERVISOR", "GET", "/api/v1/reports/execution-summary?start=2026-08-01&end=2026-12-31")
print(f"summary ({rep['generated_by']}):", rep["summary_text"][:300].replace("\n", " | "))
