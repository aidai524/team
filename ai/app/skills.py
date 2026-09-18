"""Skill resolution: slash-command lookup and {{variable}} substitution."""

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud import get_skill_by_name

VARIABLE_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def resolve_skill_message(skill_prompt: str, raw_message: str) -> str:
    """Fill ``{{variables}}`` from ``key=value`` tokens in the message.

    Example: ``/weekly-update project=mobile team=core`` fills ``{{project}}``
    and ``{{team}}``; any trailing free text is appended as extra context.
    """
    parts = raw_message.split()
    args: dict[str, str] = {}
    rest: list[str] = []
    for part in parts[1:]:  # skip the /command token
        if "=" in part:
            key, value = part.split("=", 1)
            args[key] = value
        else:
            rest.append(part)

    filled = VARIABLE_RE.sub(lambda m: args.get(m.group(1), m.group(0)), skill_prompt)

    extra = " ".join(rest).strip()
    if extra:
        filled = f"{filled}\n\nAdditional context: {extra}"
    return filled


async def resolve_slash_command(session: AsyncSession, workspace_slug: str, message: str) -> str | None:
    """Return the resolved skill prompt, or None if the message is not a slash command."""
    if not message.startswith("/"):
        return None
    name = message.split()[0][1:]
    if not name:
        return None
    skill = await get_skill_by_name(session, workspace_slug, name)
    if skill is None:
        return None
    return resolve_skill_message(skill.prompt, message)
