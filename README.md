# jargis

📄 **자기소개서 RAG 관리 솔루션 (PoC)**  
자기소개서 문항/답변을 Markdown 파일 단위로 업로드 → 문항별로 파싱/임베딩 → 벡터 검색 및 초안 작성 지원.

---

## ✨ 주요 기능

- **Markdown 업로드**
  - `# 자기소개서 N – [제목]` / `**질문**` / `**답변**` 형식 파서 지원
  - 프리뷰 단계에서 메타데이터(회사/직무/연도) 및 문항 중복 여부 확인
  - 수정/선택 후 Commit → DB 저장 + OpenAI 임베딩(pgvector)

- **RAG 기반 검색**
  - `/search` API: 자연어 질의 + 메타 필터(company/job/year)
  - pgvector 코사인 유사도 기반 상위 문항/청크 검색

- **Streamlit UI**
  - Markdown 업로드 → Preview → Commit
  - 검색 UI: 질의 입력 후 상위 문항 스니펫 확인

---

## 🏗️ 아키텍처

- **Backend**: FastAPI
- **DB**: PostgreSQL + pgvector
- **Frontend**: Streamlit
- **Embedding Model**: OpenAI `text-embedding-3-small` (dim=1536)

---

## 📂 프로젝트 구조

```

jargis/
├── app/
│   ├── main.py               # FastAPI entrypoint
│   ├── db.py                 # DB 연결
│   ├── routers/
│   │   ├── health.py
│   │   ├── upload.py         # 단일 텍스트 업로드
│   │   ├── search.py         # 벡터 검색
│   │   └── upload\_md.py      # Markdown 업로드 (preview/commit)
│   └── utils/
│       ├── normalization.py
│       ├── hashing.py
│       └── md\_parse.py
├── ui/
│   ├── Home.py               # Streamlit 홈
│   ├── api\_client.py
│   └── pages/
│       └── 1\_Materials.py    # Markdown 업로드 UI
├── schema.sql                # DB 스키마 (DDL)
└── pyproject.toml

````

---

## 🚀 실행 방법

### 1. 환경 세팅
```bash
# 가상환경 준비 (uv)
uv sync
````

### 2. 데이터베이스 준비

```bash
# PostgreSQL 확장 설치 및 테이블 생성
uv run db
```

### 3. FastAPI 실행

```bash
uv run api
# → http://127.0.0.1:8000/docs
```

### 4. Streamlit UI 실행

```bash
uv run ui
# → http://127.0.0.1:8501
```

---

## 🧪 사용 흐름

1. **\[UI] Materials 페이지**

   * Markdown 업로드 → 프리뷰 실행
   * 회사/직무/연도 수정 가능
   * 중복 문항은 자동 표시
   * 저장(Commit) 클릭 시 DB 반영 + 임베딩 생성

2. **\[UI] Home 페이지**

   * 자연어 질의 입력
   * 회사/직무/연도 필터링 가능
   * 유사 문항 스니펫 조회

---

## 📌 향후 계획

* [ ] `/search` 응답을 문항 단위로 집계 (중복 청크 병합)
* [ ] `/draft` 또는 요약 기능 추가 (질의 기반 초안 생성)
* [ ] LLM 기반 회사/직무 자동 분류 보조
* [ ] NER 기반 소재 추출/중복 제거

---

## ⚖️ 라이선스

MIT License
