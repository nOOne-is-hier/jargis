import os
import requests

API_BASE = os.getenv("JARGIS_API_BASE", "http://127.0.0.1:8000")

def healthz():
    r = requests.get(f"{API_BASE}/healthz", timeout=10)
    r.raise_for_status()
    return r.json()
