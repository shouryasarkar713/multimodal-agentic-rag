"""add document_ids to sessions

Revision ID: 002_add_session_document_ids
Revises: 001_initial_schema
Create Date: 2026-09-06 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '002_add_session_document_ids'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS document_ids JSONB DEFAULT '[]'::jsonb;")

def downgrade() -> None:
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS document_ids;")
