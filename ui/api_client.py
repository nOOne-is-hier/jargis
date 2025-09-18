# ui/api_client.py
import os
import requests

API_BASE = os.getenv("JARGIS_API_BASE", "http://127.0.0.1:8000")


def healthz():
    r = requests.get(f"{API_BASE}/healthz", timeout=10)
    r.raise_for_status()
    return r.json()


def upload(
    content: str,
    company: str | None,
    job: str | None,
    title: str | None,
    year: int | None,
):
    payload = {
        "content": content,
        "company": company or None,
        "job": job or None,
        "title": title or None,
        "year": year if year else None,
    }
    r = requests.post(f"{API_BASE}/upload", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def search(
    query: str,
    top_k: int = 5,
    company: str | None = None,
    job: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
):
    payload = {
        "query": query,
        "top_k": top_k,
        "company": company or None,
        "job": job or None,
        "year_min": year_min,
        "year_max": year_max,
    }
    r = requests.post(f"{API_BASE}/search", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def draft(question_id: int, top_k: int = 3):
    payload = {"question_id": question_id, "top_k": top_k}
    r = requests.post(f"{API_BASE}/draft", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def preview_md(file_path: str, hint_company=None, hint_job=None, hint_year=None):
    files = {"file": open(file_path, "rb")}
    data = {}
    if hint_company:
        data["hint_company"] = hint_company
    if hint_job:
        data["hint_job"] = hint_job
    if hint_year:
        data["hint_year"] = str(hint_year)
    r = requests.post(
        f"{API_BASE}/upload-md/preview", files=files, data=data, timeout=60
    )
    r.raise_for_status()
    return r.json()


def commit_md(payload: dict):
    r = requests.post(f"{API_BASE}/upload-md/commit", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()
