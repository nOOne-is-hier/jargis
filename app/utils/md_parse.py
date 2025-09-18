# app/utils/md_parse.py
from __future__ import annotations
import re
from typing import List, Dict

__all__ = ["parse_md_blocks", "extract_year_candidates"]

# 헤더 라인 예: "# 자기소개서 1 – [입행 목표 및 성장 계획]"
HEADING_RE = re.compile(
    r"^#\s*자기소개서\s+\d+\s*[–-]\s*\[(?P<title>.+?)\]\s*$", re.MULTILINE
)

# "**질문**" / "**답변**" 블록 라벨
LABEL_RE = re.compile(r"^\s*\*\*(질문|답변)\*\*\s*$", re.MULTILINE)


def _split_sections(md: str) -> List[Dict[str, str]]:
    """
    헤더 기준으로 섹션 분리. 각 섹션은 {title, body} 반환.
    """
    sections: List[Dict[str, str]] = []
    last_end = 0
    last_title = None

    for m in HEADING_RE.finditer(md):
        if last_title is not None:
            body = md[last_end : m.start()].strip()
            sections.append({"title": last_title, "body": body})
        last_title = m.group("title").strip()
        last_end = m.end()

    # 마지막 섹션
    if last_title is not None:
        body = md[last_end:].strip()
        sections.append({"title": last_title, "body": body})

    return sections


def _extract_blocks(body: str) -> Dict[str, str]:
    """
    본문에서 **질문** / **답변** 블록 추출.
    라벨 이후 다음 라벨 또는 문서 끝까지를 해당 블록으로 본다.
    """
    blocks = {"question": "", "answer": ""}

    # 라벨들의 위치를 찾고, 각 라벨 영역을 분할
    labels = list(LABEL_RE.finditer(body))
    if not labels:
        # 라벨이 없다면 전체를 답변으로 간주 (보수적)
        blocks["answer"] = body.strip()
        return blocks

    # 라벨 이름과 구간 텍스트를 묶기
    for i, lab in enumerate(labels):
        name = lab.group(1)  # "질문" or "답변"
        start = lab.end()
        end = labels[i + 1].start() if i + 1 < len(labels) else len(body)
        text = body[start:end].strip()

        if name == "질문":
            blocks["question"] = text
        elif name == "답변":
            blocks["answer"] = text

    return blocks


def parse_md_blocks(md: str) -> List[Dict[str, str]]:
    """
    고정 양식 Markdown에서 섹션을 파싱하여,
    [{"title":..., "question":..., "answer":..., "raw":...}, ...] 반환.
    """
    md = md or ""
    sections = _split_sections(md)
    results: List[Dict[str, str]] = []
    for sec in sections:
        blocks = _extract_blocks(sec["body"])
        # raw(디버그/해시용) 포함
        results.append(
            {
                "title": sec["title"],
                "question": blocks.get("question", "").strip(),
                "answer": blocks.get("answer", "").strip(),
                "raw": sec["body"].strip(),
            }
        )
    return results


_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def extract_year_candidates(text: str) -> List[int]:
    """
    본문에서 연도 후보(2000~2099)를 찾아 정수 리스트로 반환.
    정확한 year 결정은 상위 로직에서 빈도/우선순위로 판단.
    """
    return [int(y) for y in _YEAR_RE.findall(text or "") if 2000 <= int(y) <= 2099]
