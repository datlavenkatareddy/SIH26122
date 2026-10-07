"""
Upload the v6 benchmark schedule (sample_data/canonical/schedule.csv: 45 activities, 34
dependencies incl. FS/SS/FF/SF with lags, and total float) through POST /api/v1/schedules.
The newest schedule becomes the active one (new claims match against it) and its FAISS
index is built. Safe to re-run; each run adds a new schedule.

    python scripts/load_demo_schedule.py
"""
from pathlib import Path

from _demo_client import call

csv_text = (Path(__file__).resolve().parents[1] / "sample_data" / "canonical" / "schedule.csv").read_text()
status, body = call("SUPERVISOR", "POST", "/api/v1/schedules",
                    json={"project_name": "SIH26122 Canonical Demo Schedule (v6 network)",
                          "source_format": "csv", "csv_content": csv_text})
print(status, body)
