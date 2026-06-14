import contextvars

from fastmcp import FastMCP

from services.database import get_context_files
from services.generator import _call_gemini

current_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_user_id", default=None
)

mcp = FastMCP("unbiased")


@mcp.tool()
async def get_stack() -> str:
    """Returns the developer's tech stack (languages, frameworks, tools)."""
    uid = current_user_id.get()
    if uid is None:
        return "Error: not authenticated. Include your MCP token."
    files = {f.filename: f.content for f in await get_context_files(uid)}
    return files.get("stack.md", "stack.md not yet generated — log in and wait for extraction to complete.")


@mcp.tool()
async def get_projects() -> str:
    """Returns summaries of the developer's notable GitHub projects."""
    uid = current_user_id.get()
    if uid is None:
        return "Error: not authenticated. Include your MCP token."
    files = {f.filename: f.content for f in await get_context_files(uid)}
    return files.get("projects.md", "projects.md not yet generated — log in and wait for extraction to complete.")


@mcp.tool()
async def get_full_context() -> str:
    """Returns all developer context files merged into a single document."""
    uid = current_user_id.get()
    if uid is None:
        return "Error: not authenticated. Include your MCP token."
    files = await get_context_files(uid)
    if not files:
        return "No context files found — log in and wait for extraction to complete."
    return "\n\n---\n\n".join(f"# {f.filename}\n\n{f.content}" for f in files)


@mcp.tool()
async def get_context_for(task: str) -> str:
    """Returns the developer context most relevant to the given task."""
    uid = current_user_id.get()
    if uid is None:
        return "Error: not authenticated. Include your MCP token."
    files = await get_context_files(uid)
    if not files:
        return "No context files found — log in and wait for extraction to complete."
    context_text = "\n\n---\n\n".join(f"# {f.filename}\n\n{f.content}" for f in files)
    prompt = (
        f"A developer is working on: {task}\n\n"
        f"Here are their context files:\n\n{context_text}\n\n"
        "Return only the sections most relevant to this task. "
        "Include file names as headers. Be concise."
    )
    return await _call_gemini(prompt)
