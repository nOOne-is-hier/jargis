# app/utils/normalization.py
import re
import unicodedata

__all__ = ["normalize_name"]

_WHITESPACE_RE = re.compile(r"\s+")
_REMOVE_RE = re.compile(r"[^0-9a-zA-Z가-힣]+")


def normalize_name(s: str) -> str:
    """
    표준화 규칙 (회사/직무 등 고유명사에 공통 적용):
      - 유니코드 NFKC 정규화
      - 앞뒤 공백 제거
      - 전부 소문자
      - 연속 공백 1칸으로 축소
      - 영문/숫자/한글 외 문자 제거
      - 최종적으로 공백 제거(= 키값으로 쓰기 위함)
    예)
      "  LG  CNS  " -> "lgcns"
      "한화 비전(주)" -> "한화비전주" -> (원문 '이름'은 보존, normalized_name만 키로 사용)
    """
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.strip()
    s = _WHITESPACE_RE.sub(" ", s)
    s = s.lower()
    s = _REMOVE_RE.sub("", s)
    s = s.replace(" ", "")
    return s
