import os
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Get database URL from environment; default to async SQLite locally
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///decision_log.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class DecisionLogTable(Base):
    
    __tablename__ = "decision_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project: Mapped[str] = mapped_column(String(100), index=True)
    decision: Mapped[str] = mapped_column(String(500))
    rationale: Mapped[str] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

async def init_db():
    """Initializes the database by creating all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
