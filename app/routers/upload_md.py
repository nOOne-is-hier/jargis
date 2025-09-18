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
