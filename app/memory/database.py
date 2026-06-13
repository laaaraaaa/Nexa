# SQLAlchemy is our ORM — it lets us interact with PostgreSQL using Python
# instead of writing raw SQL everywhere
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

# Build the connection URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/nexa"
)

# Create the async engine — this is the core connection to PostgreSQL
# echo=True means it'll print SQL queries to terminal (useful for debugging)
engine = create_async_engine(DATABASE_URL, echo=True)

# Base class that all our database models will inherit from
Base = declarative_base()

# Session factory — every database operation happens inside a session
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency function — FastAPI will call this to get a db session
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise