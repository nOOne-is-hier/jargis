# jargis
RAG mini 프로젝트

---

CREATE DATABASE jargis
    WITH OWNER = "user"
    ENCODING = 'UTF8'
    LC_COLLATE = 'C'
    LC_CTYPE = 'C'
    TEMPLATE = template0;

---

# uv run python app/bootstrap_db.py
# uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# uv run streamlit run ui/Home.py --server.port 8501

