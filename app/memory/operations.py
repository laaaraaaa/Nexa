from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pgvector.sqlalchemy import Vector
from app.memory.models import EpisodicMemory
import uuid


async def store_memory(
    db: AsyncSession,
    repo: str,
    workflow_name: str,
    error_type: str,
    error_message: str,
    fix_attempted: str = None,
    fix_successful: bool = False,
    error_embedding: list = None,
    pr_number: int = None        # ← add this
) -> EpisodicMemory:
    """
    Store a new CI failure memory in the database.
    """
    memory = EpisodicMemory(
        id=uuid.uuid4(),
        repo=repo,
        workflow_name=workflow_name,
        error_type=error_type,
        error_message=error_message,
        fix_attempted=fix_attempted,
        fix_successful=fix_successful,
        error_embedding=error_embedding,
        pr_number=pr_number        # ← add this
    )

    db.add(memory)
    await db.commit()
    await db.refresh(memory)

    print(f"💾 Memory stored: {repo} — {error_type}")
    return memory


async def search_similar_failures(
    db: AsyncSession,
    error_embedding: list,
    limit: int = 5
) -> list[EpisodicMemory]:
    """
    Search for past failures similar to the current one.
    Uses vector cosine similarity — returns the closest matches.
    Called before attempting a fix so Nexa can learn from the past.
    """
    if error_embedding is None:
        return []

    # Cosine distance operator <=> finds the most similar vectors
    # Lower distance = more similar
    result = await db.execute(
        select(EpisodicMemory)
        .order_by(EpisodicMemory.error_embedding.cosine_distance(error_embedding))
        .limit(limit)
    )

    memories = result.scalars().all()
    print(f"🔍 Found {len(memories)} similar past failures")
    return memories


async def get_recent_failures(
    db: AsyncSession,
    repo: str,
    limit: int = 10
) -> list[EpisodicMemory]:
    """
    Get the most recent failures for a specific repo.
    Used by the orchestrator to get context about recent history.
    """
    result = await db.execute(
        select(EpisodicMemory)
        .where(EpisodicMemory.repo == repo)
        .order_by(desc(EpisodicMemory.created_at))
        .limit(limit)
    )

    return result.scalars().all()


async def mark_fix_successful(
    db: AsyncSession,
    memory_id: uuid.UUID,
    fix_attempted: str
) -> EpisodicMemory:
    """
    Update a memory entry when a fix succeeds.
    This is how Nexa learns what works.
    """
    result = await db.execute(
        select(EpisodicMemory).where(EpisodicMemory.id == memory_id)
    )
    memory = result.scalar_one_or_none()

    if memory:
        memory.fix_successful = True
        memory.fix_attempted = fix_attempted
        await db.commit()
        await db.refresh(memory)
        print(f"✅ Memory updated — fix marked successful")

    return memory