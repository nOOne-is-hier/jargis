# app/utils/hashing.py
import hashlib

__all__ = ["sha256_hex", "short_hash"]


def sha256_hex(txt: str) -> str:
    """문자열 전체에 대한 SHA-256 hexdigest (길이 64)."""
    if txt is None:
        txt = ""
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def short_hash(txt: str, n: int = 16) -> str:
    """
    짧은 해시(접두) 생성. 기본 16자.
    질문 고유성(content_hash_prefix), 청크 고유성(chunk_hash)에 사용.
    """
    return sha256_hex(txt)[:n]
