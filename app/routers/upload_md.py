# app/routers/upload_md.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from ..db import engine
from ..utils.md_parse import parse_md_blocks, extract_year_candidates
from ..utils.normalization import normalize_name
from ..utils.hashing import sha256_hex, short_hash

router = APIRouter()


# ---------- 응답 스키마 ----------
class PreviewQuestion(BaseModel):
    title: str
    question: str
    answer: str
    hash_prefix: str
    duplicate: bool
    exists_question_id: int | None = None
    content_preview: str


class PreviewResponse(BaseModel):
    document: dict
    meta: dict
    questions: list[PreviewQuestion]


# ---------- 엔드포인트 ----------
@router.post("/upload-md/preview", response_model=PreviewResponse)
async def upload_md_preview(
    file: UploadFile = File(...),
    hint_company: str | None = Form(None),
    hint_job: str | None = Form(None),
    hint_year: int | None = Form(None),
):
    """
    Markdown 파일 업로드 → 파싱 → 중복 여부 체크 (DB 저장 X)
    """
    try:
        raw_bytes = await file.read()
        raw_text = raw_bytes.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일 읽기 실패: {e}")

    # 문서 해시
    doc_hash = sha256_hex(raw_text)

    # DB에서 동일 문서 여부 확인
    with engine.connect() as conn:
        existing_doc = conn.execute(
            text("SELECT id FROM documents WHERE content_hash = :h"),
            {"h": doc_hash},
        ).fetchone()

    # 문항 파싱
    sections = parse_md_blocks(raw_text)

    # 연도 추출 후보
    year = hint_year
    if year is None:
        candidates = extract_year_candidates(raw_text)
        if candidates:
            # 단순히 최빈값 or 최대값 선택 (시연용)
            year = max(candidates)

    # 회사/직무 추정 (지금은 hint 우선)
    company = hint_company or "Unknown Company"
    job = hint_job or "Unknown Job"

    norm_company = normalize_name(company)
    norm_job = normalize_name(job)

    # DB에서 기존 company/job 있는지 조회
    with engine.connect() as conn:
        existing_company = conn.execute(
            text("SELECT id FROM companies WHERE normalized_name = :n"),
            {"n": norm_company},
        ).fetchone()
        existing_job = conn.execute(
            text("SELECT id FROM jobs WHERE normalized_name = :n"),
            {"n": norm_job},
        ).fetchone()

    # 질문 단위 중복 체크
    preview_questions: list[PreviewQuestion] = []
    with engine.connect() as conn:
        for sec in sections:
            q_text = sec["question"] or ""
            a_text = sec["answer"] or ""
            raw = sec["raw"] or ""
            prefix = short_hash(q_text + a_text, 16)

            row = conn.execute(
                text(
                    """
                    SELECT id FROM questions
                    WHERE content_hash_prefix = :p
                      AND coalesce(year,0) = coalesce(:y,0)
                """
                ),
                {"p": prefix, "y": year},
            ).fetchone()

            preview_questions.append(
                PreviewQuestion(
                    title=sec["title"],
                    question=q_text,
                    answer=a_text,
                    hash_prefix=prefix,
                    duplicate=row is not None,
                    exists_question_id=row[0] if row else None,
                    content_preview=(
                        (a_text[:120] + "...") if len(a_text) > 120 else a_text
                    ),
                )
            )

    return PreviewResponse(
        document={
            "filename": file.filename,
            "content_hash": doc_hash,
            "duplicate": existing_doc is not None,
        },
        meta={
            "company": company,
            "job": job,
            "year": year,
            "company_exists": existing_company is not None,
            "job_exists": existing_job is not None,
        },
        questions=preview_questions,
    )


# app/routers/upload_md.py (기존 preview 밑에 이어서 추가)
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy import text
from ..settings import settings
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)


# ---- 간단 청킹 (upload 라우터와 동일 규칙) ----
def simple_chunk(text: str, max_len: int = 800, overlap: int = 100) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks = []
    start, n = 0, len(text)
    while start < n:
        end = min(n, start + max_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def to_pgvector_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


# ---------- 커밋용 스키마 ----------
class CommitQuestion(BaseModel):
    title: str
    question: str
    answer: str
    hash_prefix: Optional[str] = None
    include: bool = True  # 선택적으로 특정 섹션만 저장하고 싶을 때


class CommitMeta(BaseModel):
    company: str
    job: str
    year: Optional[int] = None


class CommitDocument(BaseModel):
    filename: str
    content_hash: str
    raw_text: Optional[str] = None  # 문서가 최초 저장이면 필요, 이미 있으면 생략 가능


class CommitPayload(BaseModel):
    document: CommitDocument
    meta: CommitMeta
    questions: List[CommitQuestion] = Field(default_factory=list)


class CommitResponse(BaseModel):
    document_id: int
    company_id: Optional[int]
    job_id: Optional[int]
    year: Optional[int]
    inserted_questions: int
    skipped_questions: int
    inserted_embeddings: int


# ---------- 헬퍼: 회사/직무 upsert ----------
def upsert_company(conn, name: str) -> int:
    from ..utils.normalization import normalize_name

    norm = normalize_name(name)
    if not norm:
        # Unknown 처리 (NULL 허용 시 None 반환)
        return None
    row = conn.execute(
        text(
            """
            INSERT INTO companies(name, normalized_name)
            VALUES (:n, :nn)
            ON CONFLICT (normalized_name) DO UPDATE
            SET name = EXCLUDED.name
            RETURNING id
        """
        ),
        {"n": name.strip(), "nn": norm},
    ).first()
    if row:
        return row[0]
    # fallback: select
    return conn.execute(
        text("SELECT id FROM companies WHERE normalized_name=:nn"), {"nn": norm}
    ).scalar()


def upsert_job(conn, name: str) -> int:
    from ..utils.normalization import normalize_name

    norm = normalize_name(name)
    if not norm:
        return None
    row = conn.execute(
        text(
            """
            INSERT INTO jobs(name, normalized_name)
            VALUES (:n, :nn)
            ON CONFLICT (normalized_name) DO UPDATE
            SET name = EXCLUDED.name
            RETURNING id
        """
        ),
        {"n": name.strip(), "nn": norm},
    ).first()
    if row:
        return row[0]
    return conn.execute(
        text("SELECT id FROM jobs WHERE normalized_name=:nn"), {"nn": norm}
    ).scalar()


# ---------- /upload-md/commit ----------
@router.post("/upload-md/commit", response_model=CommitResponse)
def upload_md_commit(payload: CommitPayload):
    doc = payload.document
    meta = payload.meta
    sections = [q for q in payload.questions if q.include]

    if not sections:
        raise HTTPException(status_code=400, detail="No sections to commit")

    # 1) documents upsert (content_hash UNIQUE)
    with engine.begin() as conn:
        existing_doc = conn.execute(
            text("SELECT id FROM documents WHERE content_hash = :h"),
            {"h": doc.content_hash},
        ).fetchone()

        if existing_doc:
            document_id = existing_doc[0]
        else:
            if not doc.raw_text:
                raise HTTPException(
                    status_code=400, detail="raw_text required for new document"
                )
            row = conn.execute(
                text(
                    """
                    INSERT INTO documents(filename, content_hash, raw_text, source)
                    VALUES (:fn, :h, :raw, 'upload-md')
                    RETURNING id
                """
                ),
                {"fn": doc.filename, "h": doc.content_hash, "raw": doc.raw_text},
            ).first()
            if not row:
                raise HTTPException(status_code=500, detail="Failed to insert document")
            document_id = row[0]

        # 2) companies/jobs upsert
        company_id = upsert_company(conn, meta.company) if meta.company else None
        job_id = upsert_job(conn, meta.job) if meta.job else None

    # 3) 질문 insert (고유성 체크) + 4) 임베딩 생성/저장
    inserted_q = 0
    skipped_q = 0
    inserted_emb = 0

    # OpenAI 임베딩(배치) 준비: 섹션별로 answer 기반 청킹 → 하나의 리스트로 flatten
    all_chunks: List[tuple[int, int, str]] = []  # (temp_index, chunk_id, chunk_text)
    sec_indices: List[int] = []  # 섹션 인덱스 → all_chunks 범위 매핑

    # 3-a) 일단 questions를 insert하면서 각 question_id를 확보해야 하지만,
    # 임베딩은 answer 청크 기준 배치 생성이 효율적이므로 2단계로 처리:
    # (A) questions insert만 먼저 → 신규 question들의 (tmp list) 유지
    question_ids: List[Optional[int]] = [None] * len(sections)

    from ..utils.hashing import short_hash

    with engine.begin() as conn:
        for i, q in enumerate(sections):
            # content 구성: 질문 + 개행 + 답변 (스키마 설명상 "문항/답변 원문")
            content = (q.question or "").strip()
            if q.answer:
                content = (content + "\n\n" + q.answer.strip()).strip()

            prefix = q.hash_prefix or short_hash(content, 16)

            # 고유성 체크: (company_id, job_id, year, content_hash_prefix)
            exists_row = conn.execute(
                text(
                    """
                    SELECT id FROM questions
                    WHERE content_hash_prefix = :p
                      AND coalesce(company_id, -1) = coalesce(:cid, -1)
                      AND coalesce(job_id, -1) = coalesce(:jid, -1)
                      AND coalesce(year, 0) = coalesce(:y, 0)
                """
                ),
                {"p": prefix, "cid": company_id, "jid": job_id, "y": meta.year},
            ).fetchone()

            if exists_row:
                question_ids[i] = exists_row[0]
                skipped_q += 1
                continue

            row = conn.execute(
                text(
                    """
                    INSERT INTO questions(content, company_id, job_id, document_id, title, year, content_hash_prefix)
                    VALUES (:content, :cid, :jid, :docid, :title, :y, :prefix)
                    RETURNING id
                """
                ),
                {
                    "content": content,
                    "cid": company_id,
                    "jid": job_id,
                    "docid": document_id,
                    "title": q.title,
                    "y": meta.year,
                    "prefix": prefix,
                },
            ).first()

            if not row:
                raise HTTPException(status_code=500, detail="Failed to insert question")

            question_ids[i] = row[0]
            inserted_q += 1

    # (B) 신규/존재하는 question들에 대해 청킹 → 임베딩 배치 생성
    # 답변이 비어 있으면 질문으로 대체
    flat_chunks: List[str] = []
    chunk_map: List[tuple[int, int]] = []  # (section_index, chunk_id)

    for i, q in enumerate(sections):
        qtext = (q.answer or q.question or "").strip()
        chunks = simple_chunk(qtext, max_len=800, overlap=100)
        if not chunks:
            continue
        for idx, ck in enumerate(chunks, start=1):
            flat_chunks.append(ck)
            chunk_map.append((i, idx))

    vectors: List[List[float]] = []
    if flat_chunks:
        try:
            emb_res = client.embeddings.create(
                model=settings.embedding_model,  # "text-embedding-3-small"
                input=flat_chunks,
            )
            vectors = [d.embedding for d in emb_res.data]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"OpenAI embeddings error: {e}")

    # (C) embeddings insert
    from ..utils.hashing import short_hash

    with engine.begin() as conn:
        for (sec_idx, chunk_id), vec in zip(chunk_map, vectors):
            qid = question_ids[sec_idx]
            if not qid:
                continue
            chunk_text = flat_chunks.pop(0)  # consume in order
            chunk_hash = short_hash(chunk_text, 16)
            vec_lit = to_pgvector_literal(vec)
            # 중복 청크 방지 (question_id, chunk_hash)
            exists = conn.execute(
                text(
                    """
                    SELECT 1 FROM embeddings
                    WHERE question_id = :qid AND chunk_hash = :ch
                """
                ),
                {"qid": qid, "ch": chunk_hash},
            ).fetchone()
            if exists:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO embeddings (question_id, chunk_id, chunk_text, embedding, dim, model, chunk_hash)
                    VALUES (:qid, :cid, :ct, (:emb)::vector, :dim, :model, :ch)
                """
                ),
                {
                    "qid": qid,
                    "cid": chunk_id,
                    "ct": chunk_text,
                    "emb": vec_lit,  # "[0.123,...]" 형태의 문자열
                    "dim": len(vec),
                    "model": settings.embedding_model,
                    "ch": chunk_hash,
                },
            )

            inserted_emb += 1

    return CommitResponse(
        document_id=document_id,
        company_id=company_id,
        job_id=job_id,
        year=meta.year,
        inserted_questions=inserted_q,
        skipped_questions=skipped_q,
        inserted_embeddings=inserted_emb,
    )
