from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import admin_user
from app.db.session import get_db
from app.models.telemetry import AIRequest, ToolExecution
from app.models.user import User
from app.models.workspace import Conversation, Document

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/metrics")
async def metrics(_: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    users = await db.scalar(select(func.count(User.id)))
    conversations = await db.scalar(select(func.count(Conversation.id)))
    indexed_documents = await db.scalar(
        select(func.count(Document.id)).where(Document.status == "indexed")
    )
    ai_requests = await db.scalar(select(func.count(AIRequest.id)))
    avg_latency = await db.scalar(select(func.avg(AIRequest.latency_ms)))
    failed_requests = await db.scalar(
        select(func.count(AIRequest.id)).where(AIRequest.status == "error")
    )
    tool_rows = (
        await db.execute(
            select(
                ToolExecution.tool_name, ToolExecution.status, func.count(ToolExecution.id)
            ).group_by(ToolExecution.tool_name, ToolExecution.status)
        )
    ).all()
    return {
        "registered_users": users or 0,
        "conversations": conversations or 0,
        "indexed_documents": indexed_documents or 0,
        "ai_requests": ai_requests or 0,
        "average_response_ms": round(float(avg_latency or 0), 1),
        "ai_errors": failed_requests or 0,
        "tool_invocations": [
            {"tool": name, "status": status, "count": count} for name, status, count in tool_rows
        ],
    }
