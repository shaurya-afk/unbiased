from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from services.database import get_context_files, get_raw_data, upsert_context_file, upsert_user_token

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.session.get("github_token")
    if not token:
        return RedirectResponse("/")

    user_id = request.session.get("user_id")
    raw = await get_raw_data(user_id) if user_id else None
    repo_count = len(raw.repos_json) if raw else None

    context_files = await get_context_files(user_id) if user_id else []
    context = {f.filename: f.content for f in context_files}

    mcp_token = request.session.get("mcp_token") or (await upsert_user_token(user_id) if user_id else "")
    base_url = str(request.base_url).rstrip("/")

    return templates.TemplateResponse(request, "dashboard.html", {
        "username": request.session.get("github_username"),
        "avatar_url": request.session.get("github_avatar_url"),
        "repo_count": repo_count,
        "context": context,
        "mcp_token": mcp_token,
        "mcp_url": f"{base_url}/mcp?token={mcp_token}",
    })


@router.post("/context/goals")
async def save_goals(request: Request, content: str = Form(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/")
    await upsert_context_file(user_id, "goals.md", content)
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/context/learning")
async def save_learning(request: Request, content: str = Form(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/")
    await upsert_context_file(user_id, "learning.md", content)
    return RedirectResponse("/dashboard", status_code=303)
