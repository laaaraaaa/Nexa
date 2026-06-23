from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.memory.database import get_db
from app.memory.models import EpisodicMemory

router = APIRouter()


@router.get("/api/memories")
async def get_memories(db: AsyncSession = Depends(get_db)):
    """
    Returns all episodic memories for the dashboard.
    """
    result = await db.execute(
        select(EpisodicMemory)
        .order_by(desc(EpisodicMemory.created_at))
        .limit(50)
    )
    memories = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "repo": m.repo,
            "workflow_name": m.workflow_name,
            "error_type": m.error_type,
            "error_message": m.error_message,
            "fix_attempted": m.fix_attempted,
            "fix_successful": m.fix_successful,
            "pr_number": m.pr_number,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in memories
    ]


@router.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Returns high level stats for the dashboard header.
    """
    result = await db.execute(select(EpisodicMemory))
    memories = result.scalars().all()

    total = len(memories)
    successful = len([m for m in memories if m.fix_successful])
    with_pr = len([m for m in memories if m.pr_number])

    return {
        "total_failures": total,
        "fixes_attempted": with_pr,
        "fixes_successful": successful,
        "success_rate": round((successful / with_pr * 100) if with_pr > 0 else 0, 1)
    }