# app/routers/search.py
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from ..db import engine
from ..settings import settings

from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)

router = APIRouter()


# --------- 요청/응답 스키마 ----------
class SearchRequest(BaseModel):
    query: str = Field(..., description="검색 질의(자연어)")
    top_k: int = Field(5, ge=1, le=50)
    company: Optional[str] = Field(None, description="회사명 필터")
    job: Optional[str] = Field(None, description="직무명 필터")
    year_min: Optional[int] = Field(None, description="연도 하한")
    year_max: Optional[int] = Field(None, description="연도 상한")


class SearchHit(BaseModel):
    question_id: int
    chunk_id: int
    title: Optional[str]
    snippet: str
    company: Optional[str]
    job: Optional[str]
    year: Optional[int]
    distance: float  # pgvector cosine distance (낮을수록 유사)
    similarity: float  # 1 - distance (참고용)


class SearchResponse(BaseModel):
    hits: List[SearchHit]
    model: str


def to_pgvector_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


# --------- 엔드포인트 ----------
@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Empty query")

    # 1) 쿼리 임베딩
    try:
        emb = client.embeddings.create(
            model=settings.embedding_model,  # "text-embedding-3-small"
            input=query,
        )
        qvec = emb.data[0].embedding
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI embeddings error: {e}")

    qvec_lit = to_pgvector_literal(qvec)

    # 2) 벡터검색 + 메타 필터
    #    distance = e.embedding <-> :qvec::vector (코사인 거리, 낮을수록 근접)
    #    similarity = 1 - distance (참고용)
    filters_sql = []
    params: Dict[str, Any] = {"qvec": qvec_lit, "topk": req.top_k}

    if req.company:
        filters_sql.append("c.name ILIKE :company")
        params["company"] = f"%{req.company}%"
    if req.job:
        filters_sql.append("j.name ILIKE :job")
        params["job"] = f"%{req.job}%"
    if req.year_min is not None:
        filters_sql.append("q.year >= :ymin")
        params["ymin"] = req.year_min
    if req.year_max is not None:
        filters_sql.append("q.year <= :ymax")
        params["ymax"] = req.year_max

    where_clause = ""
    if filters_sql:
        where_clause = "WHERE " + " AND ".join(filters_sql)

    sql = f"""
        SELECT
            q.id               AS question_id,
            e.chunk_id         AS chunk_id,
            q.title            AS title,
            LEFT(e.chunk_text, 240) AS snippet,
            c.name             AS company,
            j.name             AS job,
            q.year             AS year,
            (e.embedding <-> CAST(:qvec AS vector)) AS distance,
            (1 - (e.embedding <-> CAST(:qvec AS vector))) AS similarity
        FROM embeddings e
        JOIN questions q ON q.id = e.question_id
        LEFT JOIN companies c ON c.id = q.company_id
        LEFT JOIN jobs j ON j.id = q.job_id
        {where_clause}
        ORDER BY distance ASC
        LIMIT :topk
    """

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()

    hits = [SearchHit(**row) for row in rows]
    return SearchResponse(hits=hits, model=settings.embedding_model)
