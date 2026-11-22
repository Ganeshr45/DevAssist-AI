from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.db.session import get_db
from app.models.telemetry import AIRequest, ToolExecution
from app.models.user import User
from app.models.workspace import Conversation, Document

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def overview(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    conversations = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.user_id == user.id)
    )
    documents = await db.scalar(
        select(func.count(Document.id)).where(
            Document.user_id == user.id, Document.status == "indexed"
        )
    )
    requests = await db.scalar(select(func.count(AIRequest.id)).where(AIRequest.user_id == user.id))
    avg_latency = await db.scalar(
        select(func.avg(AIRequest.latency_ms)).where(AIRequest.user_id == user.id)
    )
    failures = await db.scalar(
        select(func.count(AIRequest.id)).where(
            AIRequest.user_id == user.id, AIRequest.status == "error"
        )
    )
    tools = (
        await db.execute(
            select(ToolExecution.tool_name, func.count(ToolExecution.id))
            .where(ToolExecution.user_id == user.id)
            .group_by(ToolExecution.tool_name)
        )
    ).all()
    return {
        "conversations": conversations or 0,
        "indexed_documents": documents or 0,
        "ai_requests": requests or 0,
        "average_response_ms": round(float(avg_latency or 0), 1),
        "errors": failures or 0,
        "tool_invocations": [{"tool": name, "count": count} for name, count in tools],
    }
