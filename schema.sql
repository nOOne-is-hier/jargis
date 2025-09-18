-- schema.sql
CREATE EXTENSION IF NOT EXISTS vector;


CREATE TABLE
    IF NOT EXISTS companies (
        id SERIAL PRIMARY KEY,
        name VARCHAR(120) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT now ()
    );


CREATE TABLE
    IF NOT EXISTS jobs (
        id SERIAL PRIMARY KEY,
        name VARCHAR(120) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT now ()
    );


CREATE TABLE
    IF NOT EXISTS questions (
        id SERIAL PRIMARY KEY,
        content TEXT NOT NULL, -- 문항/답변 원문
        company_id INT REFERENCES companies (id) ON DELETE SET NULL,
        job_id INT REFERENCES jobs (id) ON DELETE SET NULL,
        created_at TIMESTAMP DEFAULT now (),
        title VARCHAR(200),
        YEAR INT
    );


CREATE TABLE
    IF NOT EXISTS materials (
        id SERIAL PRIMARY KEY,
        name VARCHAR(200) NOT NULL, -- 소재명 (프로젝트/수상 등)
        type VARCHAR(40) NOT NULL, -- 'project' | 'award' | 'cert' | 'career' | 'experience'
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


CREATE TABLE
    IF NOT EXISTS embeddings (
        id SERIAL PRIMARY KEY,
        question_id INT NOT NULL REFERENCES questions (id) ON DELETE CASCADE,
        chunk_id INT,
        chunk_text TEXT NOT NULL,
        embedding VECTOR (1536) NOT NULL, -- text-embedding-3-small
        dim SMALLINT NOT NULL DEFAULT 1536,
        model VARCHAR(120) NOT NULL, -- 예: 'text-embedding-3-small'
        created_at TIMESTAMP DEFAULT now ()
    );


-- 벡터 인덱스(코사인 거리). 데이터 커지면 lists↑
CREATE INDEX IF NOT EXISTS idx_embeddings_cosine ON embeddings USING ivfflat (embedding vector_cosine_ops)
WITH
    (lists = 100);


-- 조회 자주 쓰는 FK/컬럼 보조 인덱스
CREATE INDEX IF NOT EXISTS idx_questions_company ON questions (company_id);


CREATE INDEX IF NOT EXISTS idx_questions_job ON questions (job_id);


CREATE INDEX IF NOT EXISTS idx_embeddings_qid ON embeddings (question_id);


CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings (model);