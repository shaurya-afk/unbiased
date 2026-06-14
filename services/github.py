import asyncio
import base64
from datetime import datetime, timedelta, timezone

import httpx

GITHUB_API_URL = "https://api.github.com"
_DEP_FILES = ["requirements.txt", "package.json", "pom.xml", "go.mod"]
_semaphore = asyncio.Semaphore(10)


async def fetch_github_user(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API_URL}/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def extract_github_data(token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        repos = await _list_repos(client)
        tasks = [
            _fetch_repo_details(client, r["owner"]["login"], r["name"])
            for r in repos
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_repos = []
    languages = {}
    readmes = {}

    for repo, result in zip(repos, results):
        if isinstance(result, Exception):
            continue
        repo_langs, readme_text, dep_files = result
        all_repos.append({
            "name": repo["name"],
            "description": repo.get("description"),
            "topics": repo.get("topics", []),
            "stars": repo["stargazers_count"],
            "pushed_at": repo["pushed_at"],
            "dep_files": dep_files,
        })
        languages[repo["name"]] = repo_langs
        if readme_text:
            readmes[repo["name"]] = readme_text

    return {"repos": all_repos, "languages": languages, "readmes": readmes}


async def _list_repos(client: httpx.AsyncClient) -> list[dict]:
    two_years_ago = datetime.now(timezone.utc) - timedelta(days=730)
    resp = await client.get(
        f"{GITHUB_API_URL}/user/repos",
        params={"sort": "updated", "per_page": 100, "type": "owner"},
    )
    resp.raise_for_status()
    repos = resp.json()
    filtered = [
        r for r in repos
        if not r["fork"]
        and datetime.fromisoformat(r["pushed_at"].replace("Z", "+00:00")) > two_years_ago
    ]
    return filtered[:50]


async def _fetch_repo_details(
    client: httpx.AsyncClient, owner: str, repo: str
) -> tuple[dict, str | None, dict]:
    async with _semaphore:
        langs_coro = client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/languages")
        readme_coro = client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/readme")
        dep_coros = [
            client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{f}")
            for f in _DEP_FILES
        ]
        langs_resp, readme_resp, *dep_resps = await asyncio.gather(
            langs_coro, readme_coro, *dep_coros, return_exceptions=True
        )

    repo_langs = (
        langs_resp.json()
        if not isinstance(langs_resp, Exception) and langs_resp.status_code == 200
        else {}
    )

    readme_text = None
    if not isinstance(readme_resp, Exception) and readme_resp.status_code == 200:
        try:
            readme_text = base64.b64decode(
                readme_resp.json().get("content", "")
            ).decode("utf-8", errors="replace")
        except Exception:
            pass

    dep_files = {}
    for fname, resp in zip(_DEP_FILES, dep_resps):
        if not isinstance(resp, Exception) and resp.status_code == 200:
            try:
                dep_files[fname] = base64.b64decode(
                    resp.json().get("content", "")
                ).decode("utf-8", errors="replace")
            except Exception:
                pass

    return repo_langs, readme_text, dep_files
