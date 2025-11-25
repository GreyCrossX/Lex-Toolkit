-- Enable pgvector and create a table for legal chunk embeddings.
CREATE EXTENSION IF NOT EXISTS vector;

-- Default dimension set to 1536 (OpenAI text-embedding-3-small) to stay under
-- the 2000-dimension limit for ANN indexes. If you need 3072-dim vectors
-- (text-embedding-3-large), reduce dimension before loading or drop the ANN
-- index and use brute-force scans.
DO $$
DECLARE
  dim INTEGER := 1536;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'legal_chunks' AND column_name = 'embedding'
  ) THEN
    EXECUTE format($f$
      CREATE TABLE legal_chunks (
        chunk_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        section TEXT,
        jurisdiction TEXT,
        tokenizer_model TEXT,
        metadata JSONB,
        content TEXT,
        embedding vector(%s)
      );
    $f$, dim);
  END IF;

  -- Simple btree for doc lookups; GIN for metadata; HNSW for vector search (supports >2000 dims).
  CREATE INDEX IF NOT EXISTS idx_legal_chunks_doc ON legal_chunks(doc_id);
  CREATE INDEX IF NOT EXISTS idx_legal_chunks_section ON legal_chunks(section);
  CREATE INDEX IF NOT EXISTS idx_legal_chunks_metadata ON legal_chunks USING GIN(metadata);
  CREATE INDEX IF NOT EXISTS idx_legal_chunks_embedding
    ON legal_chunks USING hnsw (embedding vector_l2_ops) WITH (m = 16, ef_construction = 64);
END$$;
