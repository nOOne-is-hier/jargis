import os
import requests

API_BASE = os.getenv("JARGIS_API_BASE", "http://127.0.0.1:8000")


def healthz():
    r = requests.get(f"{API_BASE}/healthz", timeout=10)
    r.raise_for_status()
    return r.json()


def search(query, top_k=5, company=None, job=None, year_min=None, year_max=None):
    payload = {
        "query": query,
        "top_k": top_k,
        "company": company,
        "job": job,
        "year_min": year_min,
        "year_max": year_max,
    }
    r = requests.post(f"{API_BASE}/search", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()
