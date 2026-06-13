# SQLAlchemy column types
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

# Import the Base we created in database.py
from app.memory.database import Base


class EpisodicMemory(Base):
    """
    Episodic memory — stores what happened in each CI failure run.
    Think of this as Nexa's diary. Every failure event, every fix
    attempt, every outcome gets recorded here.
    """
    __tablename__ = "episodic_memory"

    # Unique ID for each memory entry
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Which repo and workflow failed
    repo = Column(String, nullable=False)
    workflow_name = Column(String, nullable=False)

    # The raw error from the logs
    error_type = Column(String)
    error_message = Column(Text)

    # What fix was attempted
    fix_attempted = Column(Text)
    fix_successful = Column(Boolean, default=False)

    # Vector embedding of the error — this is what makes similarity
    # search possible. 1536 is the dimension size for OpenAI embeddings
    # We'll generate these when we add the AI layer
    error_embedding = Column(Vector(1536), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<EpisodicMemory repo={self.repo} fix_successful={self.fix_successful}>"