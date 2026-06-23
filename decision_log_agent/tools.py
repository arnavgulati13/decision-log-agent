from google.adk.tools import ToolContext
from typing import List, Dict
from sqlalchemy import select, or_

from .models import DecisionLog
from .database import async_session, DecisionLogTable, init_db

_db_initialized = False

async def ensure_db_initialized():
    """Helper to lazily initialize the database tables on the first call."""
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True

async def save_decision_log(log: DecisionLog) -> str:
    """Saves a confirmed architecture decision record (ADR) to the log database.
    
    Args:
        log: The structured architecture decision record to save.
    """
    await ensure_db_initialized()
    
    async with async_session() as session:
        async with session.begin():
            db_log = DecisionLogTable(
                project=log.project,
                decision=log.decision,
                rationale=log.rationale
            )
            session.add(db_log)
        await session.commit()
        
    return f"Successfully logged decision in database for project '{log.project}': {log.decision}"

async def query_decision_logs(query: str) -> str:
    """Queries or searches the logged architecture decisions to find relevant records.
    
    Args:
        query: The specific search keyword, project name, or topic to search for (e.g., 'Project X', 'Cloud Run', or 'database'). Extract the core search term from the user's question; do not pass the full conversational question.
    """
    await ensure_db_initialized()
    
    async with async_session() as session:
        # Search across all three fields using case-insensitive LIKE
        stmt = select(DecisionLogTable).where(
            or_(
                DecisionLogTable.project.ilike(f"%{query}%"),
                DecisionLogTable.decision.ilike(f"%{query}%"),
                DecisionLogTable.rationale.ilike(f"%{query}%")
            )
        )
        result = await session.execute(stmt)
        logs = result.scalars().all()
        
    if not logs:
        return f"No decisions matching '{query}' were found in the database."
        
    results = []
    for log in logs:
        results.append(
            f"- Project: {log.project}\n"
            f"  Decision: {log.decision}\n"
            f"  Rationale: {log.rationale}\n"
            f"  Logged At: {log.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
    return "\n\n".join(results)
