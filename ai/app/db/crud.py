"""CRUD helpers for conversations and messages."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    Conversation,
    MCPConnection,
    Message,
    Skill,
    UsageLog,
    WorkspaceSetting,
)
from app.llm import ChatMessage


async def get_or_create_conversation(
    session: AsyncSession,
    workspace_slug: str | None,
    conversation_id: str | None,
    first_message: str,
) -> Conversation:
    if conversation_id:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is not None:
            return conversation

    conversation = Conversation(
        workspace_slug=workspace_slug,
        title=first_message[:80] or None,
    )
    session.add(conversation)
    await session.flush()
    return conversation


async def list_history(session: AsyncSession, conversation_id: str) -> list[ChatMessage]:
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    )
    return [ChatMessage(role=m.role, content=m.content) for m in result.scalars()]


async def add_message(session: AsyncSession, conversation_id: str, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    session.add(message)
    await session.flush()
    return message


async def list_conversations(session: AsyncSession, workspace_slug: str | None = None) -> list[Conversation]:
    query = select(Conversation).order_by(Conversation.updated_at.desc())
    if workspace_slug:
        query = query.where(Conversation.workspace_slug == workspace_slug)
    result = await session.execute(query)
    return list(result.scalars())


async def add_audit_log(
    session: AsyncSession,
    *,
    workspace_slug: str | None,
    conversation_id: str | None,
    action: str,
    params: str | None,
    status: str,
    result: str | None,
) -> AuditLog:
    log = AuditLog(
        workspace_slug=workspace_slug,
        conversation_id=conversation_id,
        action=action,
        params=params,
        status=status,
        result=result,
    )
    session.add(log)
    await session.flush()
    return log


# --- Skills ---


async def list_skills(session: AsyncSession, workspace_slug: str | None, scope: str | None = None) -> list[Skill]:
    query = select(Skill).where(Skill.workspace_slug == workspace_slug)
    if scope:
        query = query.where(Skill.scope == scope)
    result = await session.execute(query.order_by(Skill.name))
    return list(result.scalars())


async def get_skill_by_name(session: AsyncSession, workspace_slug: str | None, name: str) -> Skill | None:
    result = await session.execute(
        select(Skill)
        .where(Skill.workspace_slug == workspace_slug, Skill.name == name)
        .order_by(Skill.created_at)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_skill(
    session: AsyncSession,
    *,
    workspace_slug: str | None,
    scope: str,
    name: str,
    description: str | None,
    prompt: str,
    created_by: str | None,
) -> Skill:
    skill = Skill(
        workspace_slug=workspace_slug,
        scope=scope,
        name=name,
        description=description,
        prompt=prompt,
        created_by=created_by,
    )
    session.add(skill)
    await session.flush()
    return skill


async def delete_skill(session: AsyncSession, skill_id: str, workspace_slug: str | None) -> bool:
    skill = await session.get(Skill, skill_id)
    if skill is None or skill.workspace_slug != workspace_slug:
        return False
    await session.delete(skill)
    return True


# --- MCP connections ---


async def list_mcp_connections(session: AsyncSession) -> list[MCPConnection]:
    result = await session.execute(select(MCPConnection).order_by(MCPConnection.name))
    return list(result.scalars())


async def create_mcp_connection(
    session: AsyncSession, *, name: str, transport: str, config_json: str, enabled: bool
) -> MCPConnection:
    conn = MCPConnection(name=name, transport=transport, config_json=config_json, enabled=enabled)
    session.add(conn)
    await session.flush()
    return conn


async def delete_mcp_connection(session: AsyncSession, conn_id: str) -> bool:
    conn = await session.get(MCPConnection, conn_id)
    if conn is None:
        return False
    await session.delete(conn)
    return True


# --- Usage ---


async def add_usage_log(
    session: AsyncSession,
    *,
    workspace_slug: str | None,
    member_id: str | None,
    mode: str | None,
    model: str | None,
    provider: str | None,
    latency_ms: int | None,
    tokens_in: int | None,
    tokens_out: int | None,
) -> UsageLog:
    log = UsageLog(
        workspace_slug=workspace_slug,
        member_id=member_id,
        mode=mode,
        model=model,
        provider=provider,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    session.add(log)
    await session.flush()
    return log


async def aggregate_usage(session: AsyncSession, workspace_slug: str | None) -> dict:
    rows = await session.execute(
        select(
            UsageLog.workspace_slug,
            UsageLog.model,
            func.count().label("requests"),
            func.coalesce(func.sum(UsageLog.latency_ms), 0).label("total_latency_ms"),
        )
        .where(UsageLog.workspace_slug == workspace_slug)
        .group_by(UsageLog.workspace_slug, UsageLog.model)
    )
    return {
        "by_model": [
            {
                "workspace_slug": row.workspace_slug,
                "model": row.model,
                "requests": row.requests,
                "total_latency_ms": int(row.total_latency_ms or 0),
            }
            for row in rows
        ]
    }


# --- Workspace settings ---


async def get_workspace_setting(session: AsyncSession, workspace_slug: str) -> WorkspaceSetting | None:
    result = await session.execute(
        select(WorkspaceSetting).where(WorkspaceSetting.workspace_slug == workspace_slug)
    )
    return result.scalar_one_or_none()


async def set_ai_enabled(session: AsyncSession, workspace_slug: str, enabled: bool) -> WorkspaceSetting:
    setting = await get_workspace_setting(session, workspace_slug)
    if setting is None:
        setting = WorkspaceSetting(workspace_slug=workspace_slug, ai_enabled=enabled)
        session.add(setting)
    else:
        setting.ai_enabled = enabled
    await session.flush()
    return setting
