import os

import httpx
from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import RedirectResponse

from services.database import get_raw_data, store_raw_data, upsert_context_file, upsert_user, upsert_user_token
from services.generator import generate_context_files
from services.github import extract_github_data, fetch_github_user

router = APIRouter()

GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


@router.get("/login")
async def login():
    client_id = os.environ["GITHUB_CLIENT_ID"]
    redirect_uri = os.environ["GITHUB_REDIRECT_URI"]
    scope = "read:user repo"
    url = f"{GITHUB_OAUTH_URL}?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"
    return RedirectResponse(url)


@router.get("/auth/callback")
async def auth_callback(request: Request, code: str, background_tasks: BackgroundTasks):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": os.environ["GITHUB_CLIENT_ID"],
                "client_secret": os.environ["GITHUB_CLIENT_SECRET"],
                "code": code,
                "redirect_uri": os.environ["GITHUB_REDIRECT_URI"],
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()

    access_token = token_data["access_token"]
    user_data = await fetch_github_user(access_token)
    user_id = await upsert_user(user_data["login"], access_token)

    mcp_token = await upsert_user_token(user_id)

    request.session["github_token"] = access_token
    request.session["github_username"] = user_data["login"]
    request.session["github_avatar_url"] = user_data["avatar_url"]
    request.session["user_id"] = user_id
    request.session["mcp_token"] = mcp_token

    background_tasks.add_task(_run_extraction, user_id, access_token)

    return RedirectResponse("/dashboard")


async def _run_extraction(user_id: int, token: str):
    data = await extract_github_data(token)
    await store_raw_data(user_id, data["repos"], data["languages"], data["readmes"])
    raw = await get_raw_data(user_id)
    context = await generate_context_files(raw)
    for filename, content in context.items():
        await upsert_context_file(user_id, filename, content)
