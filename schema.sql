-- pgvector 확장
CREATE EXTENSION IF NOT EXISTS vector;


-- ======================
-- Companies / Jobs
-- ======================
CREATE TABLE
    IF NOT EXISTS companies (
        id SERIAL PRIMARY KEY,
        name VARCHAR(120) UNIQUE NOT NULL,
        normalized_name VARCHAR(160),
        created_at TIMESTAMP DEFAULT now ()
    );


CREATE UNIQUE INDEX IF NOT EXISTS ux_companies_normalized_name ON companies (normalized_name);


CREATE TABLE
    IF NOT EXISTS jobs (
        id SERIAL PRIMARY KEY,
        name VARCHAR(120) UNIQUE NOT NULL,
        normalized_name VARCHAR(160),
        created_at TIMESTAMP DEFAULT now ()
    );


CREATE UNIQUE INDEX IF NOT EXISTS ux_jobs_normalized_name ON jobs (normalized_name);


-- ======================
-- Documents (신규 추가)
-- ======================
CREATE TABLE
    IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        content_hash CHAR(64) NOT NULL, -- sha256(raw_text)
        raw_text TEXT NOT NULL,
        source VARCHAR(40) DEFAULT 'upload-md',
        uploaded_at TIMESTAMP DEFAULT now (),
        UNIQUE (content_hash)
    );


-- ======================
-- Questions
-- ======================
CREATE TABLE
    IF NOT EXISTS questions (
        id SERIAL PRIMARY KEY,
        content TEXT NOT NULL, -- 문항/답변 원문
        company_id INT REFERENCES companies (id) ON DELETE SET NULL,
        job_id INT REFERENCES jobs (id) ON DELETE SET NULL,
        document_id INT REFERENCES documents (id) ON DELETE SET NULL,
        created_at TIMESTAMP DEFAULT now (),
        title VARCHAR(200),
        YEAR INT,
        content_hash_prefix CHAR(16) -- 문항 고유성 체크용
    );


-- 고유성 보장: 같은 회사/직무/연도에서 동일한 질문 hash는 중복 금지
CREATE UNIQUE INDEX IF NOT EXISTS ux_question_identity ON questions (
    COALESCE(company_id, -1),
    COALESCE(job_id, -1),
    COALESCE(YEAR, 0),
    content_hash_prefix
);


-- ======================
-- Materials (기존 유지)
-- ======================
CREATE TABLE
    IF NOT EXISTS materials (
        id SERIAL PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        type VARCHAR(40) NOT NULL, -- 'project' | 'award' | 'cert' | ...
        institution VARCHAR(160),
        period_start DATE,
        period_end DATE,
        description TEXT,
        created_at TIMESTAMP DEFAULT now ()
    );


CREATE TABLE
    IF NOT EXISTS question_materials (
        question_id INT NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
        material_id INT NOT NULL REFERENCES materials (id) ON DELETE CASCADE,
        PRIMARY KEY (question_id, material_id)
    );


-- ======================
-- Embeddings
-- ======================
CREATE TABLE
    IF NOT EXISTS embeddings (
        id SERIAL PRIMARY KEY,
        question_id INT NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
        chunk_id INT,
        chunk_text TEXT NOT NULL,
        embedding VECTOR (1536) NOT NULL, -- text-embedding-3-small 기준
        dim SMALLINT NOT NULL DEFAULT 1536,
        model VARCHAR(120) NOT NULL,
        created_at TIMESTAMP DEFAULT now (),
        chunk_hash CHAR(16)
    );


-- 벡터 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_embeddings_cosine ON embeddings USING ivfflat (embedding vector_cosine_ops)
WITH
    (lists = 100);


-- 고유성 보장: 같은 question에서 동일한 청크는 중복 금지
CREATE UNIQUE INDEX IF NOT EXISTS ux_embedding_chunk_identity ON embeddings (question_id, chunk_hash);


-- 보조 인덱스
CREATE INDEX IF NOT EXISTS idx_questions_company ON questions (company_id);


CREATE INDEX IF NOT EXISTS idx_questions_job ON questions (job_id);


CREATE INDEX IF NOT EXISTS idx_embeddings_qid ON embeddings (question_id);


CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings (model);