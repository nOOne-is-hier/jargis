# app/routers/upload.py
from typing import Optional, List, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from ..db import engine
from ..settings import settings

# OpenAI SDK (>=1.x)
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)

router = APIRouter()


# ---------- 유틸: 간단 청킹 ----------
def simple_chunk(text: str, max_len: int = 800, overlap: int = 100) -> List[str]:
    """
    문자 길이 기반의 아주 단순한 청킹 (PoC용)
    - max_len: 청크 최대 길이(문자)
    - overlap: 이전 청크와 겹치는 길이
    """
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + max_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        # 오버랩 적용
        start = max(0, end - overlap)
    return chunks


# ---------- 요청 스키마 ----------
class UploadRequest(BaseModel):
    content: str = Field(..., description="자소서 문항/답변 원문(긴 텍스트)")
    company: Optional[str] = Field(None, description="회사명 (예: Hanwha Vision)")
    job: Optional[str] = Field(None, description="직무명 (예: Platform)")
    title: Optional[str] = Field(None, description="문항/답변 요약 제목")
    year: Optional[int] = Field(None, description="응시 연도")


# ---------- 응답 스키마 ----------
class UploadResponse(BaseModel):
    question_id: int
    chunks: int
    model: str


# ---------- 라우팅 ----------
@router.post("/upload", response_model=UploadResponse)
def upload(req: UploadRequest):
    # 1) 청킹
    chunks = simple_chunk(req.content, max_len=800, overlap=100)
    if not chunks:
        raise HTTPException(status_code=400, detail="Empty content after preprocessing")

    # 2) 회사/직무 upsert → id 확보
    with engine.begin() as conn:
        company_id = None
        job_id = None

        if req.company:
            res = conn.execute(
                text(
                    """
                    INSERT INTO companies(name)
                    VALUES (:name)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                """
                ),
                {"name": req.company.strip()},
            ).first()
            company_id = (
                res[0]
                if res
                else conn.execute(
                    text("SELECT id FROM companies WHERE name = :name"),
                    {"name": req.company.strip()},
                ).scalar()
            )

        if req.job:
            res = conn.execute(
                text(
                    """
                    INSERT INTO jobs(name)
                    VALUES (:name)
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                """
                ),
                {"name": req.job.strip()},
            ).first()
            job_id = (
                res[0]
                if res
                else conn.execute(
                    text("SELECT id FROM jobs WHERE name = :name"),
                    {"name": req.job.strip()},
                ).scalar()
            )

        # 3) questions 행 생성
        q = conn.execute(
            text(
                """
                INSERT INTO questions(content, company_id, job_id, title, year)
                VALUES (:content, :company_id, :job_id, :title, :year)
                RETURNING id
            """
            ),
            {
                "content": req.content,
                "company_id": company_id,
                "job_id": job_id,
                "title": req.title,
                "year": req.year,
            },
        ).first()
        if not q:
            raise HTTPException(status_code=500, detail="Failed to insert question")
        question_id = q[0]

    # 4) OpenAI 임베딩 호출 (배치)
    try:
        emb_res = client.embeddings.create(
            model=settings.embedding_model,  # "text-embedding-3-small"
            input=chunks,
        )
        vectors = [d.embedding for d in emb_res.data]  # List[List[float]]
    except Exception as e:
        # 실패 시 롤백을 위해 questions 삭제
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM questions WHERE id = :qid"), {"qid": question_id}
            )
        raise HTTPException(status_code(502), detail=f"OpenAI embeddings error: {e}")

    # 5) embeddings 테이블 삽입
    # pgvector는 '[v1,v2,...]' 문자열 리터럴을 받아들일 수 있음
    def to_pgvector_literal(vec: List[float]) -> str:
        return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"

    with engine.begin() as conn:
        for idx, (chunk_text, vec) in enumerate(zip(chunks, vectors), start=1):
            vec_lit = to_pgvector_literal(vec)
            conn.execute(
                text(
                    """
                INSERT INTO embeddings (question_id, chunk_id, chunk_text, embedding, dim, model)
                VALUES (:question_id, :chunk_id, :chunk_text, CAST(:embedding AS vector), :dim, :model)
                """
                ),
                {
                    "question_id": question_id,
                    "chunk_id": idx,
                    "chunk_text": chunk_text,
                    "embedding": vec_lit,
                    "dim": len(vec),
                    "model": settings.embedding_model,
                },
            )

    return UploadResponse(
        question_id=question_id,
        chunks=len(chunks),
        model=settings.embedding_model,
    )
