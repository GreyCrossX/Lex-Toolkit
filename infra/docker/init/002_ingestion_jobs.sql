-- Track ingestion jobs and their status/progress.
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    job_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    content_type TEXT,
    status TEXT NOT NULL,
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT,
    error TEXT,
    doc_ids TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status ON ingestion_jobs(status);
