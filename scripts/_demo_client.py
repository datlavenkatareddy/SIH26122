"""Tiny shared helper for the demo scripts: sign in as the seeded demo users and call the API."""
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

API = os.getenv("DEMO_API_URL", "http://127.0.0.1:8000")
ACCOUNTS = {
    "SUPERVISOR": os.getenv("DEMO_SUPERVISOR_EMAIL", "supervisor@sih26122.internal"),
    "SITE_ENGINEER": os.getenv("DEMO_ENGINEER_EMAIL", "site.engineer@sih26122.internal"),
}
PASSWORD = os.getenv("DEMO_PASSWORD", "Demo123456!")  # the demo password shown on the login screen
_tokens: dict = {}


def token(role: str) -> str:
    if role not in _tokens:
        base, key = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_ANON_KEY"]
        r = httpx.post(f"{base}/auth/v1/token?grant_type=password", headers={"apikey": key},
                       json={"email": ACCOUNTS[role], "password": PASSWORD}, timeout=20)
        if r.status_code != 200:
            sys.exit(f"Could not sign in as {role}: {r.status_code} {r.text[:200]}")
        _tokens[role] = r.json()["access_token"]
    return _tokens[role]


def call(role: str, method: str, path: str, **kw):
    r = httpx.request(method, API + path, headers={"Authorization": f"Bearer {token(role)}"}, timeout=180, **kw)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text
