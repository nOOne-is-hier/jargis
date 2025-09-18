# app/routers/draft.py
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from ..db import engine
from ..settings import settings
from openai import OpenAI

client = OpenAI(api_key=settings.openai_api_key)
router = APIRouter()


# ---------- 요청/응답 ----------
class DraftRequest(BaseModel):
    question_id: int = Field(..., description="질문 ID (questions.id)")
    top_k: int = Field(3, ge=1, le=10, description="참조할 청크 수")


class DraftResponse(BaseModel):
    question_id: int
    draft: str
    model: str


# ---------- 엔드포인트 ----------
@router.post("/draft", response_model=DraftResponse)
def draft(req: DraftRequest):
    # 1) 관련 청크 가져오기
    sql = """
        SELECT chunk_text
        FROM embeddings
        WHERE question_id = :qid
        ORDER BY chunk_id ASC
        LIMIT :topk
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql), {"qid": req.question_id, "topk": req.top_k}
        ).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No embeddings found for question {req.question_id}",
        )

    context_chunks = [r[0] for r in rows]
    context = "\n\n".join(context_chunks)

    # 2) GPT 호출
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # 빠르고 저렴한 모델 (필요시 교체 가능)
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that drafts Korean job application answers.",
                },
                {
                    "role": "user",
                    "content": f"""
다음 자기소개서 문항 관련 내용을 참고해 주세요:

{context}

이 문항에 대해 300자 내외의 한국어 초안을 작성해 주세요.
                """,
                },
            ],
            max_tokens=400,
            temperature=0.7,
        )
        draft_text = completion.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"OpenAI draft generation error: {e}"
        )

    return DraftResponse(
        question_id=req.question_id,
        draft=draft_text,
        model="gpt-4o-mini",
    )
