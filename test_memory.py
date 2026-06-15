import asyncio
from app.memory.database import AsyncSessionLocal
from app.memory.operations import store_memory, get_recent_failures

async def test():
    async with AsyncSessionLocal() as db:
        # Store a fake memory
        memory = await store_memory(
            db=db,
            repo="laaaraaaa/Nexa",
            workflow_name="Nexa Test Pipeline",
            error_type="ModuleNotFoundError",
            error_message="No module named 'requests'",
            fix_attempted="pip install requests",
            fix_successful=True
        )
        print(f"Stored memory with ID: {memory.id}")

        # Retrieve recent failures
        recent = await get_recent_failures(db=db, repo="laaaraaaa/Nexa")
        print(f"Recent failures found: {len(recent)}")
        for m in recent:
            print(f"  - {m.error_type}: {m.error_message}")

asyncio.run(test())