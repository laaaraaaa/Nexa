# This script creates all the tables in the database
# We run it once to set up the schema
import asyncio
from app.memory.database import engine, Base

# Import models so Base knows about them
from app.memory.models import EpisodicMemory

async def init_db():
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created successfully!")

if __name__ == "__main__":
    asyncio.run(init_db())
    