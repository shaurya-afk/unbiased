# unbiased

Reads your GitHub once and serves your developer context — stack, projects, experience — to Claude, Cursor, and any MCP client over a single URL.

## setup

```bash
git clone https://github.com/shaurya-afk/unbiased
cd unbiased
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
cp .env.example .env
# fill in .env
```

## env vars

| Variable | Value |
|---|---|
| `GITHUB_CLIENT_ID` | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth app client secret |
| `GITHUB_REDIRECT_URI` | `http://localhost:8000/auth/callback` (local) |
| `SECRET_KEY` | random string, 32+ chars |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host/db` |
| `GEMINI_API_KEY` | Google AI Studio API key |

## run

```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000`.

## mcp

After connecting GitHub, copy the MCP URL from your dashboard and paste it into your MCP client (Claude Desktop, Cursor, etc.) as a remote server URL.
