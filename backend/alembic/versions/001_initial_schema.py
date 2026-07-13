"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-07-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS vector;')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # 2. Create documents table
    op.execute("""
    CREATE TABLE documents (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        filename TEXT NOT NULL,
        title TEXT,
        authors TEXT[],
        abstract TEXT,
        total_pages INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'processing',
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

    # 3. Create chunks table
    op.execute("""
    CREATE TABLE chunks (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        content_type TEXT NOT NULL,
        content_text TEXT,
        content_markdown TEXT,
        page_number INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        section_title TEXT,
        bbox_json JSONB,
        image_path TEXT,
        image_caption TEXT,
        token_count INTEGER,
        text_embedding vector(1536),
        image_embedding vector(512),
        search_vector tsvector,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

    # 4. Create chunks indexes
    op.execute("CREATE INDEX idx_chunks_document_id ON chunks(document_id);")
    op.execute("CREATE INDEX idx_chunks_content_type ON chunks(content_type);")
    op.execute("CREATE INDEX idx_chunks_text_embedding ON chunks USING ivfflat (text_embedding vector_cosine_ops) WITH (lists = 100);")
    op.execute("CREATE INDEX idx_chunks_image_embedding ON chunks USING ivfflat (image_embedding vector_cosine_ops) WITH (lists = 50);")
    op.execute("CREATE INDEX idx_chunks_search_vector ON chunks USING GIN (search_vector);")

    # 5. Create triggers for auto-updating search_vector
    op.execute("""
    CREATE OR REPLACE FUNCTION chunks_search_vector_trigger() RETURNS trigger AS $$
    BEGIN
        NEW.search_vector := to_tsvector('english', COALESCE(NEW.content_text, ''));
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_chunks_search_vector
        BEFORE INSERT OR UPDATE ON chunks
        FOR EACH ROW EXECUTE FUNCTION chunks_search_vector_trigger();
    """)

    # 6. Create sessions table
    op.execute("""
    CREATE TABLE sessions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        title TEXT NOT NULL DEFAULT 'New Session',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

    # 7. Create messages table
    op.execute("""
    CREATE TABLE messages (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        citations JSONB,
        figure_refs JSONB,
        confidence REAL,
        trace_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

    # 8. Create messages indexes
    op.execute("CREATE INDEX idx_messages_session_id ON messages(session_id);")

    # 9. Create query_traces table
    op.execute("""
    CREATE TABLE query_traces (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        user_query TEXT NOT NULL,
        classified_intent TEXT,
        steps JSONB NOT NULL DEFAULT '[]',
        total_duration_ms INTEGER,
        langsmith_url TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS query_traces CASCADE;")
    op.execute("DROP TABLE IF EXISTS messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS sessions CASCADE;")
    op.execute("DROP TRIGGER IF EXISTS trg_chunks_search_vector ON chunks;")
    op.execute("DROP FUNCTION IF EXISTS chunks_search_vector_trigger CASCADE;")
    op.execute("DROP TABLE IF EXISTS chunks CASCADE;")
    op.execute("DROP TABLE IF EXISTS documents CASCADE;")
    op.execute("DROP EXTENSION IF EXISTS \"uuid-ossp\";")
    op.execute("DROP EXTENSION IF EXISTS vector;")
