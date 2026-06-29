"""Cross-database column types (PostgreSQL + SQLite dev)."""

from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB

JsonType = JSON().with_variant(JSONB(), "postgresql")
UuidType = Uuid(as_uuid=True)
